"""
Mapea filas del DataFrame a variables GraphQL de Jobber.
"""
import re
from datetime import datetime, timezone


def parse_total(raw: str) -> float:
    """Limpia '$1,234.56' → 1234.56. Lanza ValueError si no parsea."""
    cleaned = re.sub(r"[^\d.]", "", str(raw))
    if not cleaned:
        raise ValueError(f"No se pudo parsear el total: {repr(raw)}")
    return float(cleaned)


def parse_date_iso(raw: str) -> str:
    """Convierte 'MM/DD/YYYY' → 'YYYY-MM-DDT00:00:00Z'. Devuelve '' si falla."""
    raw = str(raw).strip()
    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    if not match:
        return ""
    m, d, y = match.groups()
    return f"{y}-{int(m):02d}-{int(d):02d}T00:00:00Z"


def parse_date_only(raw: str) -> str:
    """Convierte 'MM/DD/YYYY' → 'YYYY-MM-DD' (ISO8601Date). Devuelve '' si falla."""
    raw = str(raw).strip()
    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    if not match:
        return ""
    m, d, y = match.groups()
    return f"{y}-{int(m):02d}-{int(d):02d}"


def parse_address(raw: str) -> dict:
    """
    Intenta separar 'NÚMERO CALLE, CIUDAD, ESTADO ZIP' en campos.
    Jobber acepta solo street si no se puede parsear más.
    """
    raw = str(raw).strip()
    parts = [p.strip() for p in raw.split(",")]

    street  = parts[0] if len(parts) > 0 else raw
    city    = parts[1] if len(parts) > 1 else ""
    province = ""
    postal   = ""
    if len(parts) > 2:
        state_zip = parts[-1].strip().split()
        province  = state_zip[0] if state_zip else ""
        postal    = state_zip[1] if len(state_zip) > 1 else ""

    return {
        "street":     street,
        "city":       city,
        "province":   province,
        "postalCode": postal,
        "country":    "US",
    }


def addresses_match(stored: dict, candidate: str) -> bool:
    """Compara street1 de una Property guardada contra la dirección candidata."""
    stored_street    = (stored.get("street1") or "").strip().lower()
    candidate_street = parse_address(candidate).get("street", "").strip().lower()
    return stored_street == candidate_street


def build_property_input(address_str: str) -> dict:
    """Construye el objeto para PropertyCreateInput.properties[0]."""
    addr = parse_address(address_str)
    return {
        "address": {
            "street1":    addr["street"],
            "city":       addr["city"],
            "province":   addr["province"],
            "postalCode": addr["postalCode"],
            "country":    addr["country"],
        }
    }


def map_row_to_job_input(row: dict, property_id: str) -> dict:
    """
    Construye el dict de atributos para la mutation jobCreate.

    row debe tener: Job title Final, total, Start Date
    property_id: ID de la propiedad ya creada o encontrada en Jobber
    """
    unit_price = parse_total(row["total"])
    start_date = parse_date_only(row["Start Date"])

    attributes: dict = {
        "propertyId": property_id,
        "title":      row["Job title Final"],
        "invoicing": {
            "invoicingType":     "FIXED_PRICE",
            "invoicingSchedule": "ON_COMPLETION",
        },
        "lineItems": [
            {
                "name":                      "Cleaning Service",
                "description":               row["Job title Final"],
                "quantity":                  1,
                "unitPrice":                 unit_price,
                "saveToProductsAndServices": False,
            }
        ],
    }

    if start_date:
        attributes["timeframe"]  = {"startAt": start_date}
        attributes["scheduling"] = {
            "createVisits": True,
            "notifyTeam":   False,
        }

    return attributes


def validate_row(row: dict) -> str | None:
    """Devuelve mensaje de error si la fila tiene datos inválidos, None si está ok."""
    try:
        parse_total(row["total"])
    except ValueError as e:
        return str(e)
    if not str(row.get("Full Property Address", "")).strip():
        return "Dirección vacía"
    if not str(row.get("Client Name", "")).strip():
        return "Cliente vacío"
    return None
