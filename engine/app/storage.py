"""Saves each extraction to Supabase (tables in db/migrations) when SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
are set. A failed save is logged and skipped, so it never fails the extraction itself."""

import logging
from typing import Any

import httpx

from app.config import settings

log = logging.getLogger("uvicorn.error")


def store_extraction(upload: dict[str, Any], records: list[dict[str, Any]]) -> str | None:
    """Stores the upload facts and its records in one transaction. Returns the upload id, or None."""
    if not (settings.supabase_url and settings.supabase_service_role_key):
        return None
    key = settings.supabase_service_role_key
    try:
        response = httpx.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/save_upload",
            json={"p_upload": upload, "p_records": records},
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as e:
        # Only the error, never the payload: records hold personal data.
        log.warning("Could not save upload to Supabase: %s", e)
        return None
