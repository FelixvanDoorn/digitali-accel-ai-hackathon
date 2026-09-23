# Technical spec: Digitali (MVP)

Scope: the hackathon MVP from `idea-brief.md`. One web page with a live demo, one engine endpoint. Choices favour speed of building and a clean demo over scale.

## Architecture

```
Browser (Lovable app)
   │  POST /extract  (multipart: image + template_id)
   ▼
Engine (FastAPI, Python)
   1. Preprocess image (in memory)
   2. Build prompt from template
   3. Call Nebius Token Factory (vision model, JSON schema output)
   4. Validate + match against reference list
   5. Flag low confidence fields
   │  200 { records: [...], flags: [...], meta: {...} }
   ▼
Browser: editable table → confirm → export CSV / JSON
```

No database and no file storage. The photo lives in memory for the length of one request.

## Stack

| Part | Choice | Why |
| --- | --- | --- |
| Frontend | Lovable: React, Vite, TypeScript, Tailwind, shadcn/ui | Lovable's default stack; local edits sync back through GitHub |
| Engine | Python 3.12, FastAPI, Pydantic v2, uvicorn | Best image tooling, Pydantic doubles as the output validator |
| Image processing | Pillow (+ pillow-heif for iPhone photos) | Enough for the MVP; OpenCV only if deskewing turns out to matter |
| Model client | `openai` Python SDK pointed at the Token Factory base URL | Token Factory exposes an OpenAI compatible API, so switching models is a config change |
| Reference matching | rapidfuzz | Fast fuzzy match of read values against the company's list |
| Hosting | Engine as a Docker container on one small host (Render, Fly.io or a Nebius VM); frontend on Lovable hosting | One deploy each, no infra work |
| Eval | Python script in `eval/` reusing the engine's pipeline | Same code path for the demo and the measurement |

## Repos

Lovable creates and owns its own GitHub repo, and syncs with its default branch. So:

1. `digitali-web` (Lovable repo): the page, demo UI and slides. Edit in Lovable or locally; push to `main` to sync.
2. This repo: engine, templates, eval, docs.

```
engine/      FastAPI app, pipeline, Dockerfile
templates/   one JSON file per template
eval/        test set (synthetic photos + ground truth) and runner
```

## Engine

### Endpoint

`POST /extract`, multipart form:

1. `image`: JPEG, PNG, HEIC or WebP, max 10 MB.
2. `template_id`: which template to apply.

Response:

```json
{
  "records": [{ "id": 1042, "signed": true, "amount": 1380 }],
  "flags": [{ "record": 0, "field": "amount", "reason": "not_in_reference" }],
  "meta": { "model": "…", "latency_ms": 6400, "template_id": "delivery-note" }
}
```

Also `GET /templates` (list for the UI dropdown) and `GET /health`.

The call is synchronous. Expect 5 to 20 seconds; the UI shows a progress state. No queue or job IDs for the MVP.

### Pipeline

1. **Preprocess.** Apply EXIF rotation, then strip all EXIF (removes GPS). Convert to RGB JPEG, resize the long edge to about 2000 px. Encode as a base64 data URL.
2. **Prompt.** System prompt from the template: what the document is, field descriptions, reference list (inlined if short), output rules. Ask the model to return `null` for unreadable fields rather than guess.
3. **Model call.** Vision model with `response_format` set to the template's JSON schema, `temperature=0`. If the chosen model does not support structured output, fall back to JSON mode plus one repair retry.
4. **Validate.** Parse into a Pydantic model generated from the template schema. Type errors and missing required fields become flags, not failures.
5. **Match.** For fields with a reference list, fuzzy match with rapidfuzz. Exact or high score: replace with the canonical value. Low score: keep the raw value and flag `not_in_reference`.
6. **Optional second pass.** If flags exceed a threshold, send the raw output plus reference list to a cheap text model to resolve. Behind a config switch; only on if the eval shows it helps.

### Confidence

Models do not give calibrated confidence, so a field is flagged when any of these hold: the model returned `null`, schema validation failed, the reference match is weak, or (if the model exposes logprobs) the value's token probability is low. The UI highlights flagged cells; a person confirms before export.

### Templates

A template is a JSON file, written by hand for the MVP (no builder UI):

```json
{
  "id": "delivery-note",
  "name": "Delivery note",
  "description": "Handwritten delivery note, one row per delivery",
  "multi_record": true,
  "schema": { "type": "object", "properties": { "id": { "type": "integer" }, "signed": { "type": "boolean" }, "amount": { "type": "number" } }, "required": ["id"] },
  "fields": { "id": { "hint": "Order number, top left", "reference": "orders" } },
  "references": { "orders": [1040, 1041, 1042] }
}
```

For the integration use case, a caller may send its own template in the request body instead of a `template_id`.

### Config

Environment variables: `NEBIUS_API_KEY`, `NEBIUS_BASE_URL`, `VISION_MODEL`, `TEXT_MODEL`, `ALLOWED_ORIGINS`, `DEMO_API_KEY`.

## Frontend

1. Single page: idea, live demo, slides as sections.
2. Demo flow: pick template → upload or take photo (`<input type="file" accept="image/*" capture="environment">`) → preview → extract → editable table with flagged cells highlighted → confirm → export CSV or JSON (client side, no backend call).
3. Engine URL from `VITE_ENGINE_URL`. The Nebius key never reaches the browser.

## Security and privacy

1. Photos processed in memory, never written to disk or logged. Logs hold template ID, latency, model, flag counts only.
2. CORS limited to the Lovable preview and production domains.
3. Simple `X-API-Key` header for integration calls; the demo page uses a rate limited demo key to protect Token Factory credits.
4. Test data is synthetic.

## Models and evaluation

Candidates on Token Factory to confirm against the current catalogue: a small and a large open vision model (for example the Qwen VL and Gemma families), plus one closed model as baseline.

`eval/run.py` runs every test image through the pipeline for each model and reports field accuracy, reference match rate, cost per page and p50/p95 latency. The cheapest model that meets the accuracy bar becomes `VISION_MODEL`.

## Open questions

1. Which vision models on Token Factory support `response_format` with a JSON schema.
2. Where to host the engine (Nebius VM keeps everything on one provider for the pitch).
3. Whether multi page or multi photo uploads are needed for the demo.
