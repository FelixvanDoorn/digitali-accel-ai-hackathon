# Digitali

Digitali turns analogue operations into structured data, from a single photo.

Companies with large paper based operations want data driven decisions but struggle with data input and collection: forms, sheets and logs get retyped by hand, late and with errors. With Digitali, staff keep the paper they already use and send a photo. A vision model on Nebius Token Factory reads it, maps it to the company's own schema, and returns clean JSON ready for their system.

## How it works

1. **Input:** a photo of any paper form, sheet or log (web upload for the MVP, messaging apps later).
2. **Engine:** an open vision model on Nebius Token Factory, prompted with the company's template, reference data and the exact output format.
3. **Output:** validated JSON per record, for example `{"id": 1042, "signed": true, "amount": 1380}`.

Companies can use Digitali in two ways: call the engine from their own system (API in, JSON out), or use our web page to upload, review, correct and export.

## Repo

1. `idea-brief.md`: problem, scope, measurement plan and responsible design.
2. Web page (idea, live demo, pitch slides): to follow.
3. Engine (API endpoint): to follow.

Built for the Accel AI Hackathon.
