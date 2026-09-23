import json
import logging
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import FastAPI, Form, Header, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import ConfigError, check_model_config, settings
from app.images import InvalidImage, PreparedImage, prepare
from app.instructions import InvalidInstructions, clean_instructions
from app.storage import fetch_dashboard, storage_configured, store_extraction
from app.templates import Template, load_templates
from app.vision import VisionError, read_image

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Warn at startup instead of failing, so /health and the docs still work while setting up.
    try:
        check_model_config()
    except ConfigError as e:
        log.warning("Token Factory is not configured; /extract will fail until fixed.\n%s", e)
    yield


app = FastAPI(title="Digitali engine", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

templates = load_templates(settings.templates_dir)


class Flag(BaseModel):
    record: int
    field: str
    reason: str


class ExtractMeta(BaseModel):
    template_id: str
    model: str
    latency_ms: int
    image_width: int
    image_height: int
    instructions: str | None  # as cleaned and sent to the model
    upload_id: str | None = None  # id in Supabase, or None if not saved


class ExtractResponse(BaseModel):
    records: list[dict[str, Any]]
    flags: list[Flag]
    meta: ExtractMeta


def flag_records(records: list[dict[str, Any]], template: Template) -> list[Flag]:
    flags = []
    for i, record in enumerate(records):
        for field in template.schema_.get("properties", {}):
            value = record.get(field)
            if value is None:
                flags.append(Flag(record=i, field=field, reason="unreadable"))
                continue
            ref = template.fields.get(field, {}).get("reference")
            # TODO: fuzzy match with rapidfuzz and replace with the canonical value.
            if ref and value not in template.references.get(ref, []):
                flags.append(Flag(record=i, field=field, reason="not_in_reference"))
    return flags


def save_upload(prepared: PreparedImage, response: "ExtractResponse") -> None:
    """Opt-in local copy of the (metadata-free) image and result, e.g. for the eval set."""
    directory = settings.save_uploads_dir
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    (directory / f"{name}.jpg").write_bytes(prepared.jpeg)
    (directory / f"{name}.json").write_text(json.dumps(response.model_dump(), indent=2))


class TemplateSummary(BaseModel):
    id: str
    name: str
    description: str


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        check_model_config()
    except ConfigError as e:
        return {"status": "ok", "model_configured": False, "setup": str(e)}
    return {"status": "ok", "model_configured": True, "model": settings.vision_model}


@app.get("/templates")
def list_templates() -> list[TemplateSummary]:
    return [TemplateSummary(id=t.id, name=t.name, description=t.description) for t in templates.values()]


def require_api_key(x_api_key: str | None) -> None:
    if settings.engine_api_key and not secrets.compare_digest(x_api_key or "", settings.engine_api_key):
        raise HTTPException(401, "Missing or wrong X-API-Key")


@app.get("/dashboard")
async def dashboard(
    template_id: str = Query("attendance"),
    days: int = Query(30, ge=0, le=3650, description="0 means all time"),
    x_api_key: str | None = Header(None),
) -> dict[str, Any]:
    """Numbers for the dashboard: totals, uploads per day, per-field stats and the latest uploads."""
    require_api_key(x_api_key)
    template = templates.get(template_id)
    if template is None:
        raise HTTPException(404, f"Unknown template: {template_id}")
    if not storage_configured():
        raise HTTPException(503, "The database is not configured (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)")

    since = datetime.now(timezone.utc) - timedelta(days=days) if days else datetime(2000, 1, 1, tzinfo=timezone.utc)
    try:
        data = await run_in_threadpool(fetch_dashboard, template_id, since.isoformat())
    except Exception as e:  # noqa: BLE001 - any database failure is a 502 for the caller
        log.warning("dashboard template=%s failed: %s", template_id, e)
        raise HTTPException(502, "Could not load the dashboard from the database") from e

    return {
        "template": {
            "id": template.id,
            "name": template.name,
            "fields": [
                {"name": name, "type": spec.get("type", "string"), "hint": template.fields.get(name, {}).get("hint", "")}
                for name, spec in template.schema_.get("properties", {}).items()
            ],
        },
        "templates": [{"id": t.id, "name": t.name} for t in templates.values()],
        "days": days,
        "since": since.isoformat(),
        **data,
    }


@app.post("/extract")
async def extract(
    image: UploadFile,
    template_id: str = Form(...),
    instructions: str | None = Form(None),
    source: Literal["web", "api"] = Form("api"),
    x_api_key: str | None = Header(None),
) -> ExtractResponse:
    started = time.perf_counter()

    require_api_key(x_api_key)

    template = templates.get(template_id)
    if template is None:
        raise HTTPException(404, f"Unknown template: {template_id}")

    try:
        instructions = clean_instructions(instructions)
    except InvalidInstructions as e:
        raise HTTPException(422, str(e)) from e

    raw = await image.read(settings.max_upload_bytes + 1)
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(413, "Image too large")
    if not raw:
        raise HTTPException(400, "Empty upload")

    try:
        prepared = prepare(raw, settings.max_image_edge)
    except InvalidImage as e:
        raise HTTPException(415, str(e)) from e

    try:
        result = await run_in_threadpool(read_image, prepared.data_url(), template, instructions=instructions)
    except ConfigError as e:
        raise HTTPException(503, str(e)) from e
    except VisionError as e:
        log.warning("extract template=%s failed: %s", template_id, e)
        raise HTTPException(502, str(e)) from e
    records = result.records
    flags = flag_records(records, template)

    latency_ms = int((time.perf_counter() - started) * 1000)
    # Never log image content; only metadata.
    log.info("extract template=%s latency_ms=%d flags=%d", template_id, latency_ms, len(flags))

    response = ExtractResponse(
        records=records,
        flags=flags,
        meta=ExtractMeta(
            template_id=template_id,
            model=settings.vision_model,
            latency_ms=latency_ms,
            image_width=prepared.width,
            image_height=prepared.height,
            instructions=instructions,
        ),
    )
    response.meta.upload_id = await run_in_threadpool(
        store_extraction,
        {
            "template_id": template_id,
            "source": source,
            "instructions": instructions,
            "model": result.model,
            "structured_output": result.structured_output,
            "latency_ms": latency_ms,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "image_width": prepared.width,
            "image_height": prepared.height,
            "image_format": prepared.source_format,
            "record_count": len(records),
            "flag_count": len(flags),
        },
        [
            {"data": record, "flags": [{"field": f.field, "reason": f.reason} for f in flags if f.record == i]}
            for i, record in enumerate(records)
        ],
    )
    if settings.save_uploads_dir:
        save_upload(prepared, response)
    return response
