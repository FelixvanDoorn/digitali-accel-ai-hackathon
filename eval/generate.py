"""Generates a synthetic test set of photographed delivery notes with ground truth.

Usage (from the repo root):
    uv run --project engine python eval/generate.py [--count 30] [--seed 7]

Writes eval/cases/delivery-note/NNN.jpg and NNN.json ({"records": [...], "variant": {...}}).
Deterministic for a given seed and font set. Fonts are macOS system fonts; missing ones are skipped.
"""

import argparse
import json
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "cases" / "delivery-note"
REFERENCE_ORDERS = json.loads((REPO / "templates" / "delivery-note.json").read_text())["references"]["orders"]

FONT_CANDIDATES = {
    "typed": "/System/Library/Fonts/Supplemental/Arial.ttf",
    "bradley": "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf",
    "noteworthy": "/System/Library/Fonts/Noteworthy.ttc",
    "marker": "/System/Library/Fonts/MarkerFelt.ttc",
    "chalkboard": "/System/Library/Fonts/Supplemental/Chalkboard.ttc",
    "comic": "/System/Library/Fonts/Supplemental/Comic Sans MS.ttf",
}
FONTS = {name: path for name, path in FONT_CANDIDATES.items() if Path(path).is_file()}
HEADER_FONT = FONTS.get("typed") or next(iter(FONTS.values()))

W, H = 1400, 1000


def amount_text(amount: float, rng: random.Random) -> str:
    style = rng.choice(["plain", "eur", "comma", "decimals"])
    whole = amount == int(amount)
    if style == "plain":
        return f"{int(amount)}" if whole else f"{amount:.2f}"
    if style == "eur":
        return f"€ {int(amount)}" if whole else f"€ {amount:.2f}"
    if style == "comma":  # Dutch/German style decimals
        return f"{amount:.2f}".replace(".", ",")
    return f"{amount:.2f}"


def scribble(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], rng: random.Random) -> None:
    x0, y0, x1, y1 = box
    points = [(x0 + 10 + i * (x1 - x0 - 20) / 7, rng.randint(y0 + 12, y1 - 12)) for i in range(8)]
    draw.line(points, fill=(20, 30, 90), width=rng.randint(2, 4), joint="curve")


def make_records(rng: random.Random) -> list[dict]:
    records = []
    for _ in range(rng.randint(1, 4)):
        in_reference = rng.random() > 0.15
        order = rng.choice(REFERENCE_ORDERS) if in_reference else rng.randint(2000, 2999)
        amount = rng.choice([rng.randint(50, 5000), round(rng.uniform(20, 3000), 2)])
        records.append({"id": order, "signed": rng.random() > 0.3, "amount": amount})
    return records


def render(records: list[dict], font_name: str, rng: random.Random) -> Image.Image:
    img = Image.new("RGB", (W, H), (250, 248, 240))
    d = ImageDraw.Draw(img)
    header = ImageFont.truetype(HEADER_FONT, 44)
    label = ImageFont.truetype(HEADER_FONT, 30)
    hand = ImageFont.truetype(FONTS[font_name], rng.randint(34, 44))
    ink = rng.choice([(20, 20, 20), (20, 30, 90), (30, 30, 60)])

    d.text((70, 50), "DELIVERY NOTE", fill="black", font=header)
    d.text((70, 115), "Acme Logistics B.V. - Driver copy", fill=(90, 90, 90), font=label)

    cols = [70, 470, 870, 1330]
    top, row_h = 200, 150
    for i, title in enumerate(["Order no.", "Amount (EUR)", "Signature"]):
        d.text((cols[i] + 15, top + 20), title, fill="black", font=label)
    for r in range(len(records) + 1):
        d.line([(cols[0], top + 70 + r * row_h), (cols[-1], top + 70 + r * row_h)], fill="black", width=2)
    d.line([(cols[0], top), (cols[-1], top)], fill="black", width=2)
    for x in cols:
        d.line([(x, top), (x, top + 70 + len(records) * row_h)], fill="black", width=2)

    for r, rec in enumerate(records):
        y = top + 70 + r * row_h
        jitter = lambda: rng.randint(-6, 6)  # noqa: E731
        d.text((cols[0] + 25 + jitter(), y + 45 + jitter()), str(rec["id"]), fill=ink, font=hand)
        d.text((cols[1] + 25 + jitter(), y + 45 + jitter()), amount_text(rec["amount"], rng), fill=ink, font=hand)
        if rec["signed"]:
            scribble(d, (cols[2], y, cols[3], y + row_h), rng)
    return img


def degrade(img: Image.Image, rng: random.Random) -> tuple[Image.Image, dict]:
    variant = {}
    if rng.random() < 0.6:  # photo of paper on a table: rotated, with background
        angle = rng.uniform(-7, 7)
        variant["rotation"] = round(angle, 1)
        bg = Image.new("RGB", (int(W * 1.25), int(H * 1.3)), rng.choice([(110, 100, 90), (60, 60, 65), (170, 160, 140)]))
        rotated = img.rotate(angle, expand=True, fillcolor=bg.getpixel((0, 0)))
        bg.paste(rotated, ((bg.width - rotated.width) // 2, (bg.height - rotated.height) // 2))
        img = bg
    if rng.random() < 0.4:
        radius = rng.uniform(0.8, 2.0)
        variant["blur"] = round(radius, 1)
        img = img.filter(ImageFilter.GaussianBlur(radius))
    if rng.random() < 0.4:
        variant["noise"] = True
        noise = Image.effect_noise(img.size, rng.randint(20, 45)).convert("RGB")
        img = Image.blend(img, noise, 0.12)
    if rng.random() < 0.3:
        variant["dim"] = True
        img = img.point(lambda v: int(v * 0.7))
    return img, variant


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    if not FONTS:
        raise SystemExit("No usable fonts found; edit FONT_CANDIDATES in eval/generate.py.")

    rng = random.Random(args.seed)
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)

    for n in range(args.count):
        font_name = rng.choice(sorted(FONTS))
        records = make_records(rng)
        img, variant = degrade(render(records, font_name, rng), rng)
        variant["font"] = font_name
        img.save(OUT / f"{n:03d}.jpg", quality=rng.randint(60, 90))
        (OUT / f"{n:03d}.json").write_text(json.dumps({"records": records, "variant": variant}, indent=2) + "\n")

    print(f"Wrote {args.count} cases to {OUT.relative_to(REPO)} (fonts: {', '.join(sorted(FONTS))})")


if __name__ == "__main__":
    main()
