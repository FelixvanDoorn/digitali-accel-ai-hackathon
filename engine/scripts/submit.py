"""Submit one or more photos to a running engine and print the response.

Usage:
    uv run python scripts/submit.py photo.jpg [more.jpg ...] [--template delivery-note] [--prompt "..."]
        [--url http://localhost:8000]
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit photos to the Digitali engine")
    parser.add_argument("images", nargs="+", type=Path, help="photo file(s) to submit")
    parser.add_argument("--template", default="delivery-note", help="template id (default: delivery-note)")
    parser.add_argument("--prompt", help="optional instructions for the model, e.g. 'only signed rows'")
    parser.add_argument("--url", default="http://localhost:8000", help="engine base url")
    args = parser.parse_args()

    failed = 0
    with httpx.Client(base_url=args.url, timeout=120) as client:
        try:
            health = client.get("/health").json()
        except httpx.ConnectError:
            print(f"✗ cannot reach engine at {args.url}. Start it with:", file=sys.stderr)
            print("    cd engine && uv run uvicorn app.main:app --reload", file=sys.stderr)
            return 1
        if not health.get("model_configured"):
            print("✗ the engine is running but cannot call Token Factory yet.\n", file=sys.stderr)
            print(health.get("setup", "Unknown setup problem; check the engine logs."), file=sys.stderr)
            return 1

        for path in args.images:
            if not path.is_file():
                print(f"✗ {path}: file not found", file=sys.stderr)
                failed += 1
                continue

            started = time.perf_counter()
            try:
                with path.open("rb") as f:
                    res = client.post(
                        "/extract",
                        files={"image": (path.name, f)},
                        data={"template_id": args.template, **({"instructions": args.prompt} if args.prompt else {})},
                    )
            except httpx.ConnectError:
                print(f"✗ cannot reach engine at {args.url}. Is it running?", file=sys.stderr)
                return 1
            elapsed = time.perf_counter() - started

            mark = "✓" if res.is_success else "✗"
            print(f"{mark} {path.name}: HTTP {res.status_code} in {elapsed:.2f}s")
            try:
                body = res.json()
            except ValueError:
                print(res.text)
            else:
                # Error details can hold multi-line fix instructions; print them as text.
                if not res.is_success and isinstance(body.get("detail"), str):
                    print(body["detail"])
                else:
                    print(json.dumps(body, indent=2))
            if not res.is_success:
                failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
