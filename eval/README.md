# Eval

Compares vision models on Nebius Token Factory on a synthetic test set, using the engine's own pipeline (same image preparation, prompt and model call as `/extract`).

## Run

From the repo root, with the API key in `nebius_token.env`:

```sh
uv run --project engine python eval/generate.py        # (re)build the test set, deterministic per --seed
uv run --project engine python eval/run.py             # all 5 vision models, all cases
uv run --project engine python eval/run.py --models openbmb/MiniCPM-V-4_5 --limit 5
```

Each run writes `eval/results/<timestamp>/`:

1. `summary.md`: one row per model.
2. `results.jsonl`: one line per case per model with truth, prediction, tokens, cost and latency. Use it to see what went wrong.

## Test set

`cases/delivery-note/NNN.jpg` with `NNN.json` holding the ground truth (`records`) and how the image was made (`variant`: font, rotation, blur, noise, dim). Notes have 1 to 4 rows, mixed amount formats (`1380`, `€ 1380`, `1380,00`), about 30% unsigned rows and about 15% order numbers outside the reference list.

Fonts are macOS system fonts, so regenerate on a Mac to get the same set.

## Metrics

1. **Field acc.**: share of expected fields read correctly. Rows are compared by position; missed rows and failed calls count as wrong.
2. **Per field** (`id`, `signed`, `amount`): shows which field a model struggles with.
3. **Exact docs**: every field and the row count right.
4. **Structured**: calls where the model accepted the JSON schema instead of falling back to plain JSON mode.
5. **p50 / p95 s**: latency per page, including preparation.
6. **$ / 1000 pages**: from token usage and Token Factory list prices.
7. **Region**: where the model runs (relevant for EU data).

## Limits

Synthetic data is cleaner than real photos of real forms. Before deciding, add a handful of real (anonymised) photos to `cases/` with hand-typed ground truth.
