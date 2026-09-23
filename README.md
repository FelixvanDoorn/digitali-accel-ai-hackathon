# Digitali

Digitali turns the paper a microfinance loan officer already fills in into structured data, from a single photo.

Loan officers record group meetings on paper resolution sheets: who attended, who signed, who paid how much. Branch staff retype these into the core banking system by hand, which is slow, error prone and days late. With Digitali, the officer photographs the sheet, a vision model on Nebius Token Factory reads it and matches each row to a group member, and the result comes back as clean JSON ready to write against the member and the meeting date.

## How it works

1. **Input:** a photo of the sheet (web upload for the MVP, WhatsApp later).
2. **Engine:** an open vision model on Nebius Token Factory, prompted with the group's member list and the exact output format.
3. **Output:** one record per member, for example `{"member_id": 1042, "signed": true, "paid": 1380}`.

MFIs can use Digitali in two ways: call the engine from their own system (API in, JSON out), or use our web page to upload, review, correct and export.

## Repo

1. `idea-brief.md`: problem, scope, measurement plan and responsible design.
2. Web page (idea, live demo, pitch slides): to follow.
3. Engine (API endpoint): to follow.

Built for the Accel AI Hackathon.
