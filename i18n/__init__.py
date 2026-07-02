import streamlit as st
from i18n import es, en

_CATALOGS = {"es": es.STRINGS, "en": en.STRINGS}


def t(key: str, **kwargs) -> str:
    """Devuelve el string localizado para `key` en el idioma activo.

    El idioma se lee de st.session_state.lang (default 'es').
    Soporta interpolación: t("success_extracted", n=5) → "✅ 5 órdenes..."
    """
    lang = st.session_state.get("lang", "es")
    catalog = _CATALOGS.get(lang, es.STRINGS)
    text = catalog.get(key, es.STRINGS.get(key, key))
    return text.format(**kwargs) if kwargs else text
