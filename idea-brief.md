# Idea brief

## Problem

Microfinance loan officers run group meetings and record the outcome on paper: the group resolution sheet (who attended, who signed, who paid how much). Someone at the branch then retypes that sheet into the core banking system (AMBS at ASA). This is slow, error prone and delayed by days, so head office sees repayment and attendance late.

Two things have to be true for this to be worth building:

1. The sheet is legible enough for a model to read at the rate branches produce them. This is tested on real photographs, not assumed.
2. The officer gains something by sending the photo, or the photos stop arriving in week three.

## Product

A pipeline with three parts: input, engine, output.

1. **Input (accepts anything).** A photo of the sheet, sent by the loan officer (upload on our web page for the MVP, WhatsApp later). Later also shop and house photos and any other paper the officer already fills in.
2. **Engine.** A vision model on Nebius Token Factory reads the sheet and matches each row to a member of that group. The system prompt carries what to read, the group's member list from the core banking system, and the exact output format.
3. **Output (structured data).** One JSON record per member, for example `{"member_id": 1042, "signed": true, "paid": 1380}`, written against the member and the meeting date.

Two ways to use it:

1. **Integration.** An MFI calls the engine from its own system (API in, JSON out).
2. **Our tools.** An MFI without integration uses our web page for input and output: upload the photo, review and correct the extracted table, export it.

## MVP scope (hackathon)

1. **UI:** one web page with the idea, a live demo (upload photo, see extracted table, edit, export) and the pitch slides on the same page.
2. **Backend:** the engine as one API endpoint: image plus member list in, validated JSON out.
3. **Slides:** on the page, covering all six judging criteria.

Out of scope for the MVP: WhatsApp intake, writing into AMBS, shop and house photos.

## Models (to confirm on Token Factory)

1. Vision model for reading the sheet: the cheapest one that passes the test set.
2. Optional text model to validate and match names to member IDs when the vision output is uncertain.

## Measurement

A small test set of sheet photos with hand-typed ground truth. For each candidate model: field accuracy (member match, signed, amount paid), cost per sheet, latency. Compare against at least one larger model and one closed model as the baseline.

## Responsible design

Test data is synthetic or anonymised. Photos are processed and not stored. The model only proposes a table; the officer or branch reviews and confirms before anything is saved, and low confidence rows are flagged.
