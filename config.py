import os
import streamlit as st


def get_supplypro_credentials() -> tuple[str, str]:
    """Devuelve (username, password) leyendo de st.secrets o variables de entorno."""
    username = ""
    password = ""
    try:
        username = st.secrets["SUPPLYPRO_USERNAME"]
        password = st.secrets["SUPPLYPRO_PASSWORD"]
    except Exception:
        username = os.environ.get("SUPPLYPRO_USERNAME", "")
        password = os.environ.get("SUPPLYPRO_PASSWORD", "")

    if not username or not password:
        raise RuntimeError(
            "Faltan credenciales de SupplyPro. "
            "Configura SUPPLYPRO_USERNAME y SUPPLYPRO_PASSWORD en Streamlit Cloud secrets."
        )
    return username, password

SUPPLYPRO_URL = "https://www.hyphensolutions.com/MH2Supply/Login.asp"

# Mapas de reglas WorkSyncApex
SHINE_TASK_MAP = {
    "Interior Cleaning Draw 1 Base": "ROUGH CLEAN",
    "Interior Cleaning Draw 2 Final": "ROUGH RECLEAN",
    "Interior Reclean 1": "FINAL CLEAN",
    "Interior Reclean 2": "RECLEAN",
    "Interior Reclean 3": "RECLEAN",
    "Pressure Washing Draw 2": "REWASH",
    "Pressure Washing Draw 3": "REWASH",
    "Pressure Washing": "FIRST WASH",
    "Cleaning - Pre-Paint Clean": "ROUGH CLEAN",
    "Cleaning - Rough Clean": "ROUGH RECLEAN",
    "Cleaning - Final Clean": "FINAL CLEAN",
    "Cleaning - Final QA Clean": "QA CLEAN",
    "Cleaning - Quality Assurance Clean": "QA CLEAN",
    "Cleaning - TLC Re-Clean": "TLC RECLEAN",
    "Cleaning - Pressure Wash Home": "FIRST WASH",
    "Cleaning - Re-Wash Home": "REWASH",
    "Cleaning - Brick Clean": "BRICK CLEAN",
    "Rough Clean": "ROUGH CLEAN",
    "Final Clean": "FINAL CLEAN",
    "Quality Re-Walk": "QA CLEAN",
    "Interior Clean Touch Up #1": "TOUCH UP",
    "Interior Clean Touch Up #2": "TOUCH UP",
    "Power Wash": "FIRST WASH",
    "Celebration Walk Clean": "TLC RECLEAN",
}

SHINE_CLIENT_MAP = {
    r"^LGI Homes.*": "LGI Homes",
    r"^DRB Group.*": "DRB Group",
    r"^Lennar Homes.*": "Lennar Homes",
}

# Requerido por transformer.py
APEX_INSTRUCTION_REGEX = []

SHINE_SUBDIVISION_MAP = {
    "5536 Lakeside Glen Lake Series 40s": "Lakeside Glen 40s",
    "5537 Lakeside Glen Lake Series 50s": "Lakeside Glen 50s",
    "GAL - Bell Farm 50 - 2487260": "Bell Farm 50",
    "GAL - Bell Farm 60 - 2487360": "Bell Farm 60",
    "GAL - Creekside Cottages Dream - 2489260": "Creekside Cottages Dream",
    "GAL - Elizabeth - - 2485160": "Elizabeth Arbor",
    "GAL - Elizabeth - Chase Det Gar - 2485060": "Elizabeth Chase Det Gar",
    "GAL - Elizabeth - Enclave - 2485460": "Elizabeth Enclave",
    "GAL - Elizabeth - Meadows - 2485360": "Elizabeth Meadows",
    "GAL - Elizabeth - Trinity - 2484960": "Elizabeth Trinity",
    "GAL - Elizabeth - Walk - 2487160": "Elizabeth Walk",
    "GAL - Estates at New Town - 2902460": "Estates at New Town",
    "GAL - Legacy Ridge Dream - 2489960": "Legacy Ridge Dream",
    "GAL - Shannon Woods Meadows - 2486560": "Shannon Woods Meadows",
    "GAL - Shannon Woods Walk Enclave - 2486460": "Shannon Woods Walk Enclave",
    "GAL - Sullivan Farm - 2487960": "Sullivan Farm",
}
