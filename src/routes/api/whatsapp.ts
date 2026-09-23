import { createFileRoute } from "@tanstack/react-router";

// WhatsApp intake (Twilio). Twilio posts each incoming message here as a form; we read the photo with the
// Digitali engine and answer with TwiML, which Twilio sends back to the sender as a WhatsApp reply.

type EngineRecord = Record<string, unknown>;
type EngineResponse = {
  records?: EngineRecord[];
  flags?: Array<{ record: number; field: string; reason: string }>;
  meta?: { model?: string; latency_ms?: number };
};

function twiml(text: string) {
  const escaped = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return new Response(`<?xml version="1.0" encoding="UTF-8"?><Response><Message>${escaped}</Message></Response>`, {
    headers: { "Content-Type": "text/xml; charset=utf-8" },
  });
}

function blank(value: unknown) {
  return value === null || value === undefined || /^\s*(null|none|n\/a)?\s*$/i.test(String(value));
}

function formatReply(payload: EngineResponse) {
  const records = (payload.records ?? []).slice(0, 40);
  if (records.length === 0) return "I could not find any names on that photo. Please try again with the whole sheet in view and good light.";

  const flags = new Map<number, Set<string>>();
  for (const flag of payload.flags ?? []) {
    if (!flags.has(flag.record)) flags.set(flag.record, new Set());
    flags.get(flag.record)?.add(flag.field);
  }

  const signed = records.filter((r) => r["signed"] === true).length;
  const lines = records.map((r, i) => {
    const parts = [blank(r["name"]) ? "?" : String(r["name"])];
    if (!blank(r["role"])) parts.push(String(r["role"]));
    if (!blank(r["phone"])) parts.push(String(r["phone"]));
    ["role", "phone"].forEach((f) => blank(r[f]) && flags.get(i)?.add(f));
    return `${i + 1}. ${parts.join(" · ")} ${r["signed"] === true ? "✓" : "✗"}`;
  });

  const check = records
    .map((r, i) => ({ name: blank(r["name"]) ? `Row ${i + 1}` : String(r["name"]), fields: [...(flags.get(i) ?? [])] }))
    .filter((x) => x.fields.length > 0)
    .map((x) => `${x.name} (${x.fields.join(", ")})`);

  const model = (payload.meta?.model ?? "open vision model").split("/").pop();
  const seconds = payload.meta?.latency_ms ? ` in ${(payload.meta.latency_ms / 1000).toFixed(1)} s` : "";

  let text = `Attendance read: ${records.length} people, ${signed} signed.\n\n${lines.join("\n")}`;
  if (check.length) text += `\n\nPlease check: ${check.join(", ")}.`;
  text += `\n\nNothing is saved until you confirm. Read by ${model} on Nebius Token Factory${seconds}.`;
  return text.slice(0, 1550);
}

export const Route = createFileRoute("/api/whatsapp")({
  server: {
    handlers: {
      GET: async () => new Response("Digitali WhatsApp webhook is up. Twilio should POST here.", { status: 200 }),
      POST: async ({ request }) => {
        const form = await request.formData();
        const accountSid = process.env["TWILIO_ACCOUNT_SID"];
        if (accountSid && form.get("AccountSid") !== accountSid) {
          return new Response("Forbidden", { status: 403 });
        }

        const numMedia = Number(form.get("NumMedia") ?? 0);
        const mediaUrl = form.get("MediaUrl0");
        const mediaType = String(form.get("MediaContentType0") ?? "");
        if (!numMedia || typeof mediaUrl !== "string" || !mediaType.startsWith("image/")) {
          return twiml(
            "Karibu! Send me a photo of your attendance sheet and I will send back a clean list. You can add a note with the photo, for example which rows to include.",
          );
        }

        const engineUrl = process.env["ENGINE_URL"];
        if (!engineUrl) return twiml("The reader is not configured yet. Please try again later.");

        try {
          const headers: Record<string, string> = {};
          const token = process.env["TWILIO_AUTH_TOKEN"];
          if (accountSid && token && new URL(mediaUrl).hostname.endsWith("twilio.com")) {
            headers["Authorization"] = `Basic ${Buffer.from(`${accountSid}:${token}`).toString("base64")}`;
          }
          // Twilio answers the media URL with a redirect to its CDN; follow it without our credentials.
          let media = await fetch(mediaUrl, { headers, redirect: "manual" });
          const location = media.headers.get("location");
          if (media.status >= 300 && media.status < 400 && location) {
            media = await fetch(new URL(location, mediaUrl).toString());
          }
          if (!media.ok) throw new Error(`media download ${media.status}`);
          const bytes = new Uint8Array(await media.arrayBuffer());

          const body = new FormData();
          body.append("image", new Blob([bytes], { type: mediaType }), "whatsapp-photo");
          body.append("template_id", "attendance");
          const note = String(form.get("Body") ?? "").trim();
          if (note) body.append("instructions", note.slice(0, 500));

          const engineHeaders: Record<string, string> = {};
          const key = process.env["ENGINE_API_KEY"];
          if (key) engineHeaders["x-api-key"] = key;
          const response = await fetch(`${engineUrl.replace(/\/$/, "")}/extract`, { method: "POST", headers: engineHeaders, body });
          if (!response.ok) throw new Error(`engine ${response.status}: ${(await response.text()).slice(0, 200)}`);
          return twiml(formatReply((await response.json()) as EngineResponse));
        } catch (error) {
          const reason = error instanceof Error ? error.message : String(error);
          console.error(`WA-FAIL ${reason}`);
          return twiml(`Sorry, I could not read that photo. Please try again with the whole sheet in view. (${reason.slice(0, 120)})`);
        }
      },
    },
  },
});
