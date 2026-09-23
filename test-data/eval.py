"""Score a vision model on the attendance test sheets (01 to 10).

Usage:
  export NEBIUS_API_KEY=...
  python3 test-data/eval.py --model Qwen/Qwen2.5-VL-72B-Instruct --in-price 0.13 --out-price 0.40

Baseline through another OpenAI compatible endpoint (for example Vercel AI Gateway):
  python3 test-data/eval.py --base-url https://ai-gateway.vercel.sh/v1 --key-env AI_GATEWAY_API_KEY --model openai/gpt-4o-mini

Prices are USD per 1M tokens; look them up for the model you test.
"""
import argparse, base64, glob, json, os, re, time, urllib.request, urllib.error
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPT = ("Read this attendance sheet. Return every visible person as structured data. Use an empty string for missing text. "
          "Set signed to true only when a signature or clear mark is present. Put uncertain field names in lowConfidence. Never invent values.")
SCHEMA = {"type": "object", "properties": {"records": {"type": "array", "items": {"type": "object", "properties": {
    "name": {"type": "string"}, "role": {"type": "string"}, "phone": {"type": "string"}, "signed": {"type": "boolean"},
    "lowConfidence": {"type": "array", "items": {"type": "string", "enum": ["name", "role", "phone", "signed"]}}},
    "required": ["name", "role", "phone", "signed", "lowConfidence"], "additionalProperties": False}}},
    "required": ["records"], "additionalProperties": False}

def norm(s): return re.sub(r"[^a-z0-9]", "", str(s).lower())

def call(args, path):
    img = base64.b64encode(open(path, "rb").read()).decode()
    body = {"model": args.model, "temperature": 0, "messages": [{"role": "user", "content": [
        {"type": "text", "text": PROMPT}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}]}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "attendance_records", "strict": True, "schema": SCHEMA}}}
    req = urllib.request.Request(args.base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {os.environ[args.key_env]}", "Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as r: payload = json.load(r)
    return payload, time.time() - t0

def score(truth, pred):
    """Match predicted rows to true rows by name similarity, then compare fields."""
    fields = ["name", "role", "phone", "signed"]
    used, correct, total = set(), 0, len(truth) * len(fields)
    for t in truth:
        best, bi = 0, None
        for i, p in enumerate(pred):
            if i in used: continue
            s = SequenceMatcher(None, norm(t["name"]), norm(p.get("name", ""))).ratio()
            if s > best: best, bi = s, i
        if bi is None or best < 0.6: continue
        used.add(bi); p = pred[bi]
        for f in fields:
            correct += (t[f] == p.get(f)) if f == "signed" else (norm(t[f]) == norm(p.get(f, "")))
    return correct, total, len(pred) - len(used)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default="https://api.tokenfactory.nebius.com/v1")
    ap.add_argument("--key-env", default="NEBIUS_API_KEY")
    ap.add_argument("--in-price", type=float, default=0.0)
    ap.add_argument("--out-price", type=float, default=0.0)
    args = ap.parse_args()
    rows, C, T, lat, cost = [], 0, 0, [], 0.0
    for gt in sorted(glob.glob(os.path.join(HERE, "ground-truth", "*attendance*.json"))):
        name = os.path.basename(gt)[:-5]; truth = json.load(open(gt))
        try:
            payload, secs = call(args, os.path.join(HERE, "photos", name + ".jpg"))
            pred = json.loads(payload["choices"][0]["message"]["content"])["records"]
            u = payload.get("usage", {})
            c = (u.get("prompt_tokens", 0) * args.in_price + u.get("completion_tokens", 0) * args.out_price) / 1e6
            ok, tot, extra = score(truth["records"], pred)
        except urllib.error.HTTPError as e:
            print(f"{name}: HTTP {e.code} {e.read().decode()[:300]}"); continue
        except Exception as e:
            print(f"{name}: failed ({e})"); continue
        C += ok; T += tot; lat.append(secs); cost += c
        rows.append((name, truth["difficulty"], ok / tot, secs, c, extra))
        print(f"{name:32s} {truth['difficulty']:7s} accuracy {ok/tot:6.1%}  {secs:5.1f}s  ${c:.5f}  extra rows {extra}")
    if rows:
        print(f"\n{args.model}: field accuracy {C/T:.1%} over {len(rows)} sheets, median latency {sorted(lat)[len(lat)//2]:.1f}s, "
              f"avg cost per page ${cost/len(rows):.5f}")
        out = os.path.join(HERE, "results", re.sub(r"[^A-Za-z0-9.-]", "_", args.model) + ".json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump({"model": args.model, "field_accuracy": C / T, "sheets": len(rows), "median_latency_s": sorted(lat)[len(lat)//2],
                   "avg_cost_per_page_usd": cost / len(rows), "per_sheet": rows}, open(out, "w"), indent=2)
        print("saved", out)

if __name__ == "__main__": main()
