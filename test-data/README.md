# Test data

15 synthetic handwritten documents, photographed style (rotation, perspective, shadow, blur, JPEG noise), each with a ground truth file. All names and numbers are invented.

| # | Document | Difficulty | Schema |
| --- | --- | --- | --- |
| 01 to 10 | Attendance sheets: ruled table, lined paper, grid paper, free notebook list | 2 easy, 4 medium, 4 hard | Same as the engine: name, role, phone, signed |
| 11 | Meeting minutes | medium | attendees, decisions, actions |
| 12 | Handwritten receipt | easy | items, totals |
| 13 | Savings ledger | hard | member, paid, balance |
| 14 | Field visit note | hard | farmer, crops, issues, requests |
| 15 | Stock count | medium | item, opening, closing |

Each row on the attendance sheets uses a different handwriting, because each member writes their own line. Hard sheets add crossed out corrections, stronger blur, shadow and perspective. Some phones and roles are left blank on purpose; the ground truth has an empty string there.

Sheets 11 to 15 test the "all sorts of inputs" claim. The current engine prompt only handles attendance, so they need their own prompt and schema.

## Run the eval

```
export NEBIUS_API_KEY=your-key
python3 test-data/eval.py --model MODEL_ID --in-price IN --out-price OUT
```

`eval.py` scores sheets 01 to 10 on field accuracy (name, role, phone, signed), latency and cost per page, and saves a summary in `test-data/results/`. Run it once per model to fill the measurement slide.

`generate.py` rebuilds the set (needs the handwriting fonts in a `fonts/` folder next to it).
