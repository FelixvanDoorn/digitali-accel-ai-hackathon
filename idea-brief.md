# Idea brief: Digitali

## Problem

Many companies still run large parts of their operations on paper and other analogue formats: field forms, sign-off sheets, delivery notes, inspection checklists, handwritten logs, whiteboards, photos of shelves or sites. They want to move to data driven decision making, but the data never reaches a system, or it arrives late and wrong because someone retypes it by hand.

The bottleneck is not analytics. It is data input and collection. Replacing the paper with new apps and devices is expensive, slow to roll out and often rejected by frontline staff. So the paper stays, and the decisions stay gut based.

Two things have to be true for this to be worth building:

1. The analogue input is legible enough for a model to read at the rate the operation produces it. This is tested on real photographs, not assumed.
2. The person sending the input gains something by doing it, or the inputs stop arriving in week three.

## Product

Digitali is the place a company goes to turn its analogue operations into structured data, without changing how frontline staff work. The staff keep filling in the paper they already use; they only take a photo.

A pipeline with three parts: input, engine, output.

1. **Input (accepts anything).** A photo or scan of whatever the operation already produces: forms, sheets, notes, receipts, site photos. Web upload for the MVP; messaging apps and email later.
2. **Engine.** A vision model on Nebius Token Factory reads the input and maps it to the company's own schema. The prompt carries what to read, any reference data from the company's system (for example the list of valid IDs to match against), and the exact output format.
3. **Output (structured data).** Validated JSON per record, for example `{"id": 1042, "signed": true, "amount": 1380}`, ready to write into the company's system or export.

Two ways to use it:

1. **Integration.** A company calls the engine from its own system: image and schema in, JSON out.
2. **Our tools.** A company without integration uses our web page for input and output: upload, review and correct the extracted table, export.

Setup should be easy: a company defines one template (which fields, which reference list) and can start sending photos the same day.

## MVP scope (hackathon)

1. **UI:** one web page with the idea, a live demo (upload a photo of a paper form, see the extracted table, edit, export) and the pitch slides on the same page.
2. **Backend:** the engine as one API endpoint: image plus template in, validated JSON out.
3. **Slides:** on the page, covering all six judging criteria.

Out of scope for the MVP: messaging app intake, direct writes into client systems, template builder UI.

## Models (to confirm on Token Factory)

1. Vision model for reading the input: the cheapest one that passes the test set.
2. Optional text model to validate the output and match entries against the reference list when the vision output is uncertain.

## Measurement

A small test set of photographed paper forms with hand-typed ground truth. For each candidate model: field accuracy, reference match rate, cost per page, latency. Compare against at least one larger open model and one closed model as the baseline.

## Responsible design

Test data is synthetic. Photos are processed and not stored. The model only proposes structured data; a person reviews and confirms before anything is saved, and low confidence fields are flagged.
