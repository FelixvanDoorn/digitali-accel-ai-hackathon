"""Saves each extraction to Supabase (tables in db/migrations) when SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
are set. A failed save is logged and skipped, so it never fails the extraction itself."""

import logging
from typing import Any

import httpx

from app.config import settings

log = logging.getLogger("uvicorn.error")


def _rpc(function: str, payload: dict[str, Any]) -> Any:
    key = settings.supabase_service_role_key
    response = httpx.post(
        f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/{function}",
        json=payload,
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def storage_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_role_key)


def store_extraction(upload: dict[str, Any], records: list[dict[str, Any]]) -> str | None:
    """Stores the upload facts and its records in one transaction. Returns the upload id, or None."""
    if not storage_configured():
        return None
    try:
        return _rpc("save_upload", {"p_upload": upload, "p_records": records})
    except (httpx.HTTPError, ValueError) as e:
        # Only the error, never the payload: records hold personal data.
        log.warning("Could not save upload to Supabase: %s", e)
        return None


# A field's most common values are only passed on when it looks like a category (few values that repeat),
# so names, phone numbers and other personal, mostly-unique values never reach the dashboard.
MAX_CATEGORY_VALUES = 10


def fetch_dashboard(template_id: str, since: str) -> dict[str, Any]:
    """Dashboard numbers for one template since an ISO timestamp (db/migrations/002_dashboard.sql)."""
    data = _rpc("dashboard", {"p_template_id": template_id, "p_since": since})
    for field in data["fields"]:
        filled = field["records"] - field["empty"]
        if not (0 < field["distinct"] <= MAX_CATEGORY_VALUES and field["distinct"] * 2 <= filled):
            field["top"] = []
    return data
