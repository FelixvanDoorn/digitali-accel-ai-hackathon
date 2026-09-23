# Digitali product site

## Goal
Build a polished hackathon-ready Digitali website that makes the paper-to-data transformation tangible, demonstrates real document extraction through Nebius Token Factory, and presents the pitch deck on the same page.

## Experience
- Lead with Digitali and the core promise: one photo turns analogue operations into structured workflows.
- Show the paper problem across attendance, finance, lending, inspections, and field operations.
- Create an interactive phone-style demo: upload or photograph a form, watch it scan, review editable extracted fields and confidence, choose a workflow, then export JSON.
- Keep photos ephemeral: process them without saving; require human confirmation before export.
- Add an on-page, navigable pitch deck covering problem, insight, product, implementation, measurement, and responsible design.
- Include the API-in/JSON-out integration path without building the out-of-scope template builder or direct client-system writes.

## Visual direction
- Follow the supplied Swahili coast and Indian Ocean brief exactly: warm chokaa plaster, mwani green, restrained turmeric, Fraunces headings, Work Sans body, arch photography placeholders, kanga borders, and flat square-cornered layouts.
- Build the exact Digitali arch-and-drop SVG assets and reusable lowercase wordmark.
- Avoid dark sections except the requested green footer, gradients, glow, glass, tech labels, fake statistics, looping scanner effects, generic SaaS cards, and invented claims.
- Keep the page calm, lightweight, mobile-first, and short enough to scan quickly.

## Technical details
- Use the existing TanStack Start app and keep the repository's Vercel configuration authoritative.
- Add a server-only Nebius request boundary using `NEBIUS_API_KEY` and the current Token Factory multimodal chat-completions contract.
- Validate upload type and size, send the image as a data URL, request strict JSON, validate the response, and surface provider errors precisely.
- Discover a compatible vision model from Nebius rather than hardcoding an unverified model; prefer a documented Qwen vision model when available.
- Keep the browser workflow resilient with loading, failure, correction, reset, download, and reduced-motion states.
- Add route-specific metadata and verify build health plus desktop/mobile interaction.

## Deployment
- Check GitHub before changes whenever repository access is available.
- Keep Vercel as the deployment target. Do not use Lovable publishing for this project.
