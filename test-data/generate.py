"""Generate synthetic handwritten test sheets with ground truth for the Digitali engine."""
import json, math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

random.seed(23); np.random.seed(23)
BASE = os.path.dirname(os.path.abspath(__file__))
FONTS = sorted(os.path.join(BASE, "fonts", f) for f in os.listdir(os.path.join(BASE, "fonts")) if f.endswith(".woff"))
OUT = os.path.join(BASE, "testdata")
os.makedirs(os.path.join(OUT, "photos"), exist_ok=True)
os.makedirs(os.path.join(OUT, "ground-truth"), exist_ok=True)

W, H = 1700, 2200
INKS = [(22, 38, 110), (18, 18, 24), (30, 55, 140), (40, 40, 60)]
FIRST = ["Amina", "Neema", "Rehema", "Fatma", "Zawadi", "Halima", "Grace", "Esther", "Mwanaisha", "Joyce", "Asha", "Upendo", "Mariam", "Saida", "Winnie", "Faraji", "Baraka", "Juma", "Hassan", "Salim", "Peter", "Daudi", "Omari", "Tumaini", "Rukia", "Josephine", "Imani", "Subira", "Pendo", "Khadija"]
LAST = ["Hassan", "Juma", "Ali", "Said", "Mwangi", "Otieno", "Mushi", "Kimaro", "Njoroge", "Wanjiru", "Omondi", "Mbwana", "Shabani", "Rashidi", "Kariuki", "Akinyi", "Mollel", "Lyimo", "Swai", "Achieng"]
ROLES = ["Member"] * 6 + ["Chair", "Treasurer", "Secretary"]

def font(path, size): return ImageFont.truetype(path, size)
def phone(): return f"07{random.randint(10,99)} {random.randint(100,999)} {random.randint(100,999)}"
def names(n):
    out, seen = [], set()
    while len(out) < n:
        nm = f"{random.choice(FIRST)} {random.choice(LAST)}"
        if nm not in seen: seen.add(nm); out.append(nm)
    return out

def paper(kind):
    base = np.array(random.choice([(247, 244, 234), (242, 238, 226), (250, 248, 242), (238, 233, 218)]), dtype=np.float32)
    img = np.ones((H, W, 3), np.float32) * base
    img += np.random.normal(0, 3, (H, W, 1))
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    if kind == "lined":
        for y in range(260, H - 80, 64): d.line([(60, y), (W - 60, y)], fill=(160, 190, 215), width=2)
        d.line([(170, 0), (170, H)], fill=(220, 140, 140), width=2)
    elif kind == "grid":
        for y in range(0, H, 50): d.line([(0, y), (W, y)], fill=(200, 215, 225), width=1)
        for x in range(0, W, 50): d.line([(x, 0), (x, H)], fill=(200, 215, 225), width=1)
    return im

def fit(text, fpath, size, maxw):
    while size > 24 and font(fpath, size).getlength(text) * 1.15 > maxw: size -= 2
    return size

def hand(im, xy, text, fpath, size, ink, jitter=True, maxw=None):
    """Draw text word by word with small rotation and baseline wobble."""
    x, y = xy
    if maxw: size = fit(text, fpath, size, maxw)
    f = font(fpath, size)
    for word in text.split(" "):
        if not word:
            x += size * 0.3; continue
        bbox = f.getbbox(word)
        w, h = bbox[2] + 10, bbox[3] + int(size * 0.5)
        layer = Image.new("L", (w + 20, h + 20), 0)
        ImageDraw.Draw(layer).text((10, 10), word, font=f, fill=255)
        if jitter: layer = layer.rotate(random.uniform(-3, 3), resample=Image.BICUBIC, expand=True)
        dy = random.randint(-3, 3) if jitter else 0
        alpha = layer.point(lambda v: int(v * random.uniform(0.82, 0.97)))
        im.paste(Image.new("RGB", layer.size, ink), (int(x) - 10, int(y) - 10 + dy), alpha)
        x += bbox[2] + f.getlength(" ") * random.uniform(0.9, 1.4)
    return x

def signature(d, x, y, ink, w=170):
    pts, cx = [], x
    for i in range(random.randint(14, 22)):
        cx += w / 18; pts.append((cx, y + random.randint(-22, 18)))
    d.line(pts, fill=ink, width=3, joint="curve")
    d.line([(x + 10, y + 20), (x + w * 0.8, y + 14)], fill=ink, width=2)

def tick(d, x, y, ink):
    d.line([(x, y + 12), (x + 12, y + 26), (x + 38, y - 8)], fill=ink, width=5)

def cross_out(d, x0, y0, x1, ink, size=50):
    d.line([(x0 - 4, y0 + int(size * 0.62)), (x1 + 4, y0 + int(size * 0.55))], fill=ink, width=4)

def photo(im, hard=False):
    """Make a scan look like a phone photo: background, rotation, perspective, light, blur, noise."""
    bg_col = random.choice([(96, 72, 52), (60, 60, 64), (140, 120, 96), (180, 170, 150)])
    bw, bh = int(W * 1.18), int(H * 1.14)
    bg = Image.new("RGB", (bw, bh), bg_col)
    bg = Image.fromarray(np.clip(np.array(bg, np.float32) + np.random.normal(0, 8, (bh, bw, 1)), 0, 255).astype(np.uint8))
    rot = im.rotate(random.uniform(-6, 6) if hard else random.uniform(-3, 3), resample=Image.BICUBIC, expand=True, fillcolor=bg_col)
    bg.paste(rot, ((bw - rot.width) // 2, (bh - rot.height) // 2))
    # perspective
    m = 0.06 if hard else 0.03
    dx = [random.uniform(-m, m) * bw for _ in range(4)]; dy = [random.uniform(-m, m) * bh for _ in range(4)]
    src = [(0 + dx[0], 0 + dy[0]), (bw + dx[1], 0 + dy[1]), (bw + dx[2], bh + dy[2]), (0 + dx[3], bh + dy[3])]
    dst = [(0, 0), (bw, 0), (bw, bh), (0, bh)]
    A = []; B = []
    for (xs, ys), (xd, yd) in zip(src, dst):
        A += [[xd, yd, 1, 0, 0, 0, -xs * xd, -xs * yd], [0, 0, 0, xd, yd, 1, -ys * xd, -ys * yd]]; B += [xs, ys]
    coeffs = np.linalg.solve(np.array(A), np.array(B))
    img = bg.transform((bw, bh), Image.PERSPECTIVE, coeffs, Image.BICUBIC, fillcolor=bg_col)
    # uneven lighting and shadow
    a = np.array(img, np.float32)
    yy, xx = np.mgrid[0:bh, 0:bw]
    cx, cy = random.uniform(0.2, 0.8) * bw, random.uniform(0.2, 0.8) * bh
    light = 1.0 - 0.18 * (np.hypot(xx - cx, yy - cy) / np.hypot(bw, bh))
    if hard or random.random() < 0.5:
        sx = random.uniform(0.5, 0.9) * bw
        light *= np.where(xx > sx, random.uniform(0.72, 0.85), 1.0)
    a *= light[..., None] * random.uniform(0.9, 1.02)
    a += np.random.normal(0, 5 if hard else 3, a.shape)
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(random.uniform(1.0, 1.6) if hard else random.uniform(0.4, 0.9)))
    img = img.resize((int(bw * 0.72), int(bh * 0.72)), Image.LANCZOS)
    return img

def save(idx, slug, im, truth, hard=False):
    name = f"{idx:02d}-{slug}"
    photo(im, hard).save(os.path.join(OUT, "photos", name + ".jpg"), quality=random.randint(68, 82))
    with open(os.path.join(OUT, "ground-truth", name + ".json"), "w") as f:
        json.dump(truth, f, indent=2, ensure_ascii=False)
    print(name, truth.get("difficulty"))

# ---------- attendance sheets (engine schema) ----------
GROUPS = ["Jumuiya ya Tumaini", "Umoja Women Group", "Kilimo Bora Farmers", "Neema Savings Group", "Mwanga Youth Group", "Faraja Chama", "Shamba Letu Coop", "Upendo VSLA", "Pamoja Traders", "Baraka Fishers Group"]

def attendance(idx, style, difficulty):
    kind = {"table": "plain", "lined": "lined", "grid": "grid", "notebook": "lined"}[style]
    im = paper(kind); d = ImageDraw.Draw(im)
    ink = random.choice(INKS)
    head_font = random.choice(FONTS)
    group = GROUPS[idx - 1]
    date = f"{random.randint(1,28)}/{random.randint(1,12)}/2026"
    n = random.randint(6, 12)
    people = []
    for nm in names(n):
        people.append({"name": nm, "role": random.choice(ROLES), "phone": phone(), "signed": random.random() > 0.2, "lowConfidence": []})
    # realism: some missing phones / roles
    for p in random.sample(people, k=random.randint(0, 2)): p["phone"] = ""
    if difficulty != "easy":
        for p in random.sample(people, k=random.randint(1, 3)): p["role"] = ""
    hand(im, (200 if kind == "lined" else 110, 90), f"{group}", head_font, 72, ink)
    hand(im, (200 if kind == "lined" else 110, 185), f"Attendance  {date}", head_font, 54, ink)
    y0 = 300
    if style == "table":
        cols = [110, 640, 1000, 1360, W - 110]
        RH = 100
        d.rectangle([cols[0], y0, cols[-1], y0 + RH * (n + 1)], outline=(40, 40, 40), width=3)
        for c in cols[1:-1]: d.line([(c, y0), (c, y0 + RH * (n + 1))], fill=(40, 40, 40), width=3)
        for r in range(1, n + 1): d.line([(cols[0], y0 + RH * r), (cols[-1], y0 + RH * r)], fill=(60, 60, 60), width=2)
        for i, h in enumerate(["Name", "Role", "Phone", "Sign"]): hand(im, (cols[i] + 15, y0 + 10), h, head_font, 46, ink, False)
        rows_y = [y0 + RH * (r + 1) + 18 for r in range(n)]
        xs = [c + 15 for c in cols[:4]]
    else:
        rows_y = [y0 + 20 + (i * (128 if style == "notebook" else 110)) for i in range(n)]
        xs = [200 if kind == "lined" else 110, 760, 1080, 1440]
        if style == "grid":
            for i, h in enumerate(["NAME", "POSITION", "SIMU", "SAHIHI"]): hand(im, (xs[i], y0 + 10), h, head_font, 40, ink, False)
            rows_y = [y + 90 for y in rows_y]
    for i, (p, y) in enumerate(zip(people, rows_y)):
        fpath = random.choice(FONTS)  # each member writes their own row
        pink = random.choice(INKS)
        size = random.randint(40, 48) if style == "table" else random.randint(46, 58)
        colw = [xs[1] - xs[0] - 30, xs[2] - xs[1] - 30, xs[3] - xs[2] - 30]
        if style == "notebook":
            # free-form line: "1. Name - role - phone" and tick at end
            text = f"{i+1}. {p['name']}"
            if p["role"]: text += f" ({p['role'].lower()})"
            if p["phone"]: text += f"  {p['phone']}"
            end = hand(im, (xs[0], y), text, fpath, size, pink, maxw=W - xs[0] - 300)
            if p["signed"]: signature(d, min(end + 40, W - 260), y + 30, pink, 160)
            continue
        if difficulty == "hard" and i == 1:
            # crossed-out wrong name, correction written after it
            wrong = random.choice(FIRST)
            size = fit(wrong + " " + p["name"], fpath, size, colw[0])
            e = hand(im, (xs[0], y), wrong, fpath, size, pink)
            cross_out(d, xs[0], y, e - 20, pink, size)
            hand(im, (e + 20, y), p["name"], fpath, size, pink)
        else:
            hand(im, (xs[0], y), p["name"], fpath, size, pink, maxw=colw[0])
        if p["role"]: hand(im, (xs[1], y), p["role"], fpath, size - 6, pink, maxw=colw[1])
        if p["phone"]: hand(im, (xs[2], y), p["phone"], fpath, size - 8, pink, maxw=colw[2])
        if p["signed"]:
            if style == "grid" or random.random() < 0.4: tick(d, xs[3] + 30, y + 12, pink)
            else: signature(d, xs[3], y + 28, pink, 150)
    truth = {"document_type": "attendance_sheet", "difficulty": difficulty, "group": group, "date": date,
             "records": [{k: p[k] for k in ["name", "role", "phone", "signed", "lowConfidence"]} for p in people]}
    save(idx, "attendance-" + style, im, truth, hard=difficulty == "hard")

plan = [("table", "easy"), ("table", "medium"), ("lined", "easy"), ("lined", "medium"), ("grid", "medium"),
        ("notebook", "medium"), ("table", "hard"), ("lined", "hard"), ("grid", "hard"), ("notebook", "hard")]
for i, (s, dfc) in enumerate(plan, 1): attendance(i, s, dfc)

# ---------- unstructured documents ----------
def lines_doc(idx, slug, kind, lines, truth, difficulty="medium", size=54, gap=92):
    im = paper(kind); ink = random.choice(INKS); fpath = random.choice(FONTS)
    y = 110
    for ln in lines:
        if ln == "": y += gap // 2; continue
        indent = 200 if kind == "lined" else 110
        if ln.startswith("  "): indent += 60; ln = ln.strip()
        f = font(fpath, size); maxw = (W - indent - 100) / 1.15; cur = ""
        for word in ln.split(" "):
            if cur and f.getlength(cur + " " + word) > maxw:
                hand(im, (indent, y), cur, fpath, size, ink); y += gap; cur = word; indent = max(indent, (200 if kind == "lined" else 110) + 60)
            else: cur = (cur + " " + word).strip()
        hand(im, (indent, y), cur, fpath, size, ink); y += gap
    truth["difficulty"] = difficulty
    save(idx, slug, im, truth, hard=difficulty == "hard")

att = names(9)
lines_doc(11, "meeting-minutes", "lined", [
    "Minutes  Upendo VSLA  12/8/2026", "Present: " + ", ".join(att) + " (9 total)",
    "Apologies: Pendo Mushi", "",
    "1. Savings this week TSh 184,000", "2. Loan to Asha Ali approved TSh 250,000", "  repay over 6 months",
    "3. Next meeting moved to Thursday 19/8", "", "Action: Treasurer to open M-Pesa", "  account by 30/8",
], {"document_type": "meeting_minutes", "group": "Upendo VSLA", "date": "12/8/2026", "attendees": att, "attendee_count": 9,
    "apologies": ["Pendo Mushi"], "savings_collected_tsh": 184000,
    "decisions": ["Loan to Asha Ali approved TSh 250,000, repay over 6 months", "Next meeting moved to Thursday 19/8"],
    "actions": [{"owner": "Treasurer", "action": "Open M-Pesa account", "due": "30/8"}]})

items = [("Maize seed 2kg", 3, 4500), ("Fertiliser DAP 50kg", 1, 72000), ("Hoe", 2, 8000), ("Sprayer hire", 1, 5000)]
total = sum(q * p for _, q, p in items)
lines_doc(12, "receipt", "plain", ["Duka la Pamoja", "Receipt no 0457   3/9/2026", ""] +
          [f"{n}  x{q}  {q*p:,}" for n, q, p in items] + ["", f"TOTAL  {total:,}", "Paid cash. Asante"],
          {"document_type": "receipt", "vendor": "Duka la Pamoja", "receipt_no": "0457", "date": "3/9/2026",
           "items": [{"item": n, "qty": q, "line_total": q * p} for n, q, p in items], "total": total, "payment": "cash"},
          difficulty="easy", size=60, gap=100)

members = names(8); ledger = []
for m in members:
    paid = random.choice([5000, 10000, 10000, 15000, 20000, 0]); bal = random.choice([0, 25000, 40000, 60000, 80000])
    ledger.append({"name": m, "paid_tsh": paid, "balance_tsh": bal})
lines_doc(13, "savings-ledger", "grid", ["Neema Savings  week 36", "Name        paid      balance", ""] +
          [f"{r['name']}   {r['paid_tsh']:,}   {r['balance_tsh']:,}" for r in ledger] + ["", f"Total paid {sum(r['paid_tsh'] for r in ledger):,}"],
          {"document_type": "savings_ledger", "group": "Neema Savings", "week": 36, "entries": ledger,
           "total_paid_tsh": sum(r["paid_tsh"] for r in ledger)}, difficulty="hard", size=50, gap=96)

lines_doc(14, "field-visit-note", "lined", [
    "Field visit 21/7/2026", "Farmer: Baraka Otieno, Kisumu West", "Crop: maize + beans, approx 2.5 acres",
    "Germination good, some fall armyworm", "  on the east plot", "Advised spraying within 1 week",
    "Wants loan for irrigation pump", "  (est. KSh 45,000)", "Follow up: 4/8", "Officer: G. Wanjiru",
], {"document_type": "field_visit_note", "date": "21/7/2026", "farmer": "Baraka Otieno", "location": "Kisumu West",
    "crops": ["maize", "beans"], "acreage": 2.5, "issues": ["fall armyworm on east plot"],
    "advice": ["spray within 1 week"], "requests": [{"type": "loan", "purpose": "irrigation pump", "amount_ksh": 45000}],
    "follow_up": "4/8", "officer": "G. Wanjiru"}, difficulty="hard")

stock = [("Rice 25kg", 14, 11), ("Sugar 1kg", 60, 48), ("Cooking oil 3L", 22, 22), ("Soap bar", 120, 97), ("Matches", 200, 180)]
lines_doc(15, "stock-count", "plain", ["Stock count  Pamoja Traders", "30/9/2026", "", "item   opening   closing"] +
          [f"{n}   {o}   {c}" for n, o, c in stock] + ["", "counted by: Juma S."],
          {"document_type": "stock_count", "shop": "Pamoja Traders", "date": "30/9/2026",
           "items": [{"item": n, "opening": o, "closing": c, "sold": o - c} for n, o, c in stock], "counted_by": "Juma S."},
          difficulty="medium", size=56, gap=98)
