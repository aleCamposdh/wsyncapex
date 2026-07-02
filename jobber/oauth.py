"""
Flujo OAuth 2.0 para Jobber (Authorization Code Grant).
"""
import secrets
import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from jobber import storage
import logger as _log

_logger = _log.get(__name__)

AUTHORIZE_URL = "https://api.getjobber.com/api/oauth/authorize"
TOKEN_URL     = "https://api.getjobber.com/api/oauth/token"


def _client_id() -> str:
    return st.secrets["JOBBER_CLIENT_ID"]


def _client_secret() -> str:
    return st.secrets["JOBBER_CLIENT_SECRET"]


def _redirect_uri() -> str:
    return st.secrets.get("APP_URL", "https://localhost:8501/")


def build_auth_url() -> tuple[str, str]:
    """Devuelve (url, state). Guarda state en session_state para validarlo al volver."""
    state = secrets.token_urlsafe(16)
    st.session_state["oauth_state"] = state
    params = {
        "response_type": "code",
        "client_id":     _client_id(),
        "redirect_uri":  _redirect_uri(),
        "state":         state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}", state


def exchange_code(code: str) -> dict:
    """Intercambia el authorization code por access + refresh tokens."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id":     _client_id(),
            "client_secret": _client_secret(),
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  _redirect_uri(),
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_tokens(refresh_token: str) -> dict:
    """Obtiene nuevos tokens usando el refresh token."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id":     _client_id(),
            "client_secret": _client_secret(),
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if "warning" in data:
        _logger.warning("Jobber refresh warning: %s", data["warning"])

    return data


def save_token_response(data: dict, account_id: str = "", account_name: str = "") -> None:
    """Persiste los tokens recibidos del token endpoint."""
    expires_in = int(data.get("expires_in", 3600))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    storage.save_tokens(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=expires_at,
        account_id=account_id,
        account_name=account_name,
    )


def handle_callback() -> bool:
    """
    Detecta ?code=... en la URL (callback de Jobber) y completa el flujo.
    Devuelve True si procesó un callback nuevo, False si no había nada que hacer.
    """
    params = st.query_params
    code  = params.get("code")
    state = params.get("state")

    if not code:
        return False

    st.query_params.clear()

    saved_state = st.session_state.pop("oauth_state", None)
    if saved_state and state != saved_state:
        st.error("❌ OAuth state mismatch — posible ataque CSRF. Intenta de nuevo.")
        return True

    try:
        data = exchange_code(code)
        save_token_response(data)
        st.session_state["jobber_just_connected"] = True
    except Exception as e:
        st.session_state["jobber_connect_error"] = str(e)

    return True
