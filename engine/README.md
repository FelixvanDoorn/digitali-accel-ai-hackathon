# Digitali engine

FastAPI service: photo of a paper form plus a template in, structured JSON out. See `../tech-spec.md`.

## Setup

1. Save your Token Factory API key, on its own, in `nebius_token.env` at the repo root. It is git-ignored. (Or set `NEBIUS_API_KEY` in `engine/.env`, which takes precedence.)
2. `cp .env.example .env` and set `VISION_MODEL`, for example `openbmb/MiniCPM-V-4_5`.

If either is missing, the engine still starts. The startup log, `GET /health` and `scripts/submit.py` say what is wrong and how to fix it.

## Run locally

```sh
uv sync
uv run uvicorn app.main:app --reload
```

Then open http://localhost:8000/docs.

Submit photos from another terminal:

```sh
uv run python scripts/submit.py photo.jpg
uv run python scripts/submit.py photos/*.jpg --template delivery-note --url http://localhost:8000
```

To keep uploaded photos and results locally (e.g. to build the eval set), set `SAVE_UPLOADS_DIR=uploads` in `.env`. Leave it empty to store nothing.

## Test

The tests mock Token Factory, so they need no API key.

```sh
uv run pytest
```

## Docker

From the repo root:

```sh
docker build -f engine/Dockerfile -t digitali-engine .
docker run -p 8000:8000 --env-file engine/.env digitali-engine
```
