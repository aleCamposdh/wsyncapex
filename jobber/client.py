"""
Cliente GraphQL para Jobber con refresh automático de tokens y retry con backoff.
"""
import time
import requests
from datetime import datetime, timedelta, timezone

from jobber import storage, oauth
import logger as _log

logger = _log.get(__name__)

GRAPHQL_URL     = "https://api.getjobber.com/api/graphql"
API_VERSION     = "2025-01-20"
EXPIRY_MARGIN   = timedelta(minutes=2)
MAX_RETRIES     = 3


class JobberAuthError(Exception):
    """Token inválido o expirado sin posibilidad de refresh."""


class JobberClient:
    def __init__(self):
        self._load_tokens()

    def _load_tokens(self) -> None:
        row = storage.get_tokens()
        if not row:
            raise JobberAuthError("No hay tokens guardados. Conecta con Jobber primero.")
        self._access_token  = row["access_token"]
        self._refresh_token = row["refresh_token"]
        self._expires_at    = datetime.fromisoformat(row["expires_at"])
        self._account_id    = row.get("account_id", "")
        self._account_name  = row.get("account_name", "")

    def _ensure_fresh_token(self) -> None:
        now = datetime.now(timezone.utc)
        expires = self._expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        if now < expires - EXPIRY_MARGIN:
            return

        logger.info("Access token por expirar, refrescando...")
        try:
            data = oauth.refresh_tokens(self._refresh_token)
        except requests.HTTPError as e:
            body = e.response.text if e.response else str(e)
            if "invalid" in body.lower() or "not valid" in body.lower():
                storage.clear_tokens()
                raise JobberAuthError(
                    "Refresh token inválido. Por favor, reconecta con Jobber."
                ) from e
            raise

        oauth.save_token_response(
            data,
            account_id=self._account_id,
            account_name=self._account_name,
        )
        self._load_tokens()

    def execute(self, query: str, variables: dict | None = None) -> dict:
        """Ejecuta un query/mutation GraphQL. Maneja throttling y refresh automático."""
        variables = variables or {}
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            self._ensure_fresh_token()

            headers = {
                "Authorization":             f"Bearer {self._access_token}",
                "Content-Type":              "application/json",
                "X-JOBBER-GRAPHQL-VERSION":  API_VERSION,
            }

            try:
                resp = requests.post(
                    GRAPHQL_URL,
                    json={"query": query, "variables": variables},
                    headers=headers,
                    timeout=30,
                )
            except requests.RequestException as e:
                last_error = e
                time.sleep(2 ** attempt)
                continue

            if resp.status_code == 401:
                logger.warning("401 recibido, intentando refresh...")
                try:
                    data = oauth.refresh_tokens(self._refresh_token)
                    oauth.save_token_response(data, self._account_id, self._account_name)
                    self._load_tokens()
                    continue
                except Exception:
                    storage.clear_tokens()
                    raise JobberAuthError("Token inválido y refresh falló. Reconecta con Jobber.")

            if resp.status_code == 429:
                wait = 2 ** attempt
                logger.warning("429 Too Many Requests, esperando %ss...", wait)
                time.sleep(wait)
                last_error = Exception("429 Too Many Requests")
                continue

            resp.raise_for_status()
            result = resp.json()

            if "extensions" in result and "cost" in result["extensions"]:
                cost = result["extensions"]["cost"]
                logger.debug(
                    "Query cost: actual=%s, available=%s",
                    cost.get("actualQueryCost"),
                    cost.get("throttleStatus", {}).get("currentlyAvailable"),
                )

            errors = result.get("errors", [])
            if errors:
                codes = [e.get("extensions", {}).get("code") for e in errors]
                if "THROTTLED" in codes:
                    throttle = result.get("extensions", {}).get("cost", {}).get("throttleStatus", {})
                    available = throttle.get("currentlyAvailable", 0)
                    restore   = throttle.get("restoreRate", 500)
                    wait = max(1, (10000 - available) / max(restore, 1))
                    wait = min(wait, 30)
                    logger.warning("THROTTLED, esperando %.1fs...", wait)
                    time.sleep(wait)
                    last_error = Exception("GraphQL THROTTLED")
                    continue
                messages = [e.get("message", str(e)) for e in errors]
                logger.error("GraphQL errors: %s", messages)
                raise Exception(f"Jobber API error: {' | '.join(messages)}")

            if "data" not in result:
                logger.error("Respuesta sin 'data': %s", result)
                raise Exception(f"Respuesta inesperada de Jobber: {result}")

            return result

        raise last_error or Exception("Máximo de reintentos alcanzado.")

    def fetch_account(self) -> dict:
        """Obtiene nombre e id de la cuenta conectada."""
        result = self.execute("query { account { id name } }")
        return result["data"]["account"]

    def enrich_account_info(self) -> None:
        """Actualiza account_id / account_name en storage tras la primera conexión."""
        account = self.fetch_account()
        tokens  = storage.get_tokens()
        if tokens:
            storage.save_tokens(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                expires_at=datetime.fromisoformat(tokens["expires_at"]),
                account_id=account["id"],
                account_name=account["name"],
            )
            self._account_id   = account["id"]
            self._account_name = account["name"]
