import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import ConfigError, check_model_config, settings
from app.images import InvalidImage, PreparedImage, prepare
from app.instructions import InvalidInstructions, clean_instructions
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


@app.post("/extract")
async def extract(
    image: UploadFile, template_id: str = Form(...), instructions: str | None = Form(None)
) -> ExtractResponse:
    started = time.perf_counter()

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
    if settings.save_uploads_dir:
        save_upload(prepared, response)
    return response
