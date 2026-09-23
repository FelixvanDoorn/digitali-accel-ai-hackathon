import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

const inputSchema = z.object({
  dataUrl: z.string().max(9_500_000),
  mimeType: z.enum(["image/jpeg", "image/png", "image/webp"]),
  prompt: z.string().trim().max(500).optional(),
});

const recordSchema = z.object({
  name: z.string(),
  role: z.string(),
  phone: z.string(),
  signed: z.boolean(),
  lowConfidence: z.array(z.enum(["name", "role", "phone", "signed"])),
});

const resultSchema = z.object({ records: z.array(recordSchema).max(50), source: z.string().optional() });

export type ExtractedRecord = z.infer<typeof recordSchema>;

type EngineResponse = {
  records?: Array<Record<string, unknown>>;
  flags?: Array<{ record: number; field: string; reason: string }>;
  meta?: { model?: string; latency_ms?: number };
};

const FIELDS = ["name", "role", "phone", "signed"] as const;

async function extractViaEngine(engineUrl: string, data: z.infer<typeof inputSchema>, prompt?: string) {
  const base64 = data.dataUrl.slice(data.dataUrl.indexOf(",") + 1);
  const bytes = Uint8Array.from(Buffer.from(base64, "base64"));
  const form = new FormData();
  form.append("image", new Blob([bytes], { type: data.mimeType }), "photo");
  form.append("template_id", "attendance");
  if (prompt) form.append("instructions", prompt);

  const headers: Record<string, string> = {};
  const key = process.env["ENGINE_API_KEY"];
  if (key) headers["x-api-key"] = key;

  const response = await fetch(`${engineUrl.replace(/\/$/, "")}/extract`, { method: "POST", headers, body: form });
  if (!response.ok) {
    const detail = await response.text();
    console.error(`Engine request failed [${response.status}]: ${detail}`);
    throw new Error(`The photo could not be read (${response.status}). Please try again.`);
  }
  const payload = (await response.json()) as EngineResponse;
  const records = (payload.records ?? []).slice(0, 50).map((raw, index) => {
    const flagged = new Set((payload.flags ?? []).filter((f) => f.record === index).map((f) => f.field));
    const text = (field: "name" | "role" | "phone") => {
      const value = raw[field];
      if (value === null || value === undefined || /^\s*(null|none|n\/a)?\s*$/i.test(String(value))) {
        flagged.add(field);
        return "";
      }
      return String(value);
    };
    const signedRaw = raw["signed"];
    if (typeof signedRaw !== "boolean") flagged.add("signed");
    return {
      name: text("name"),
      role: text("role"),
      phone: text("phone"),
      signed: signedRaw === true,
      lowConfidence: FIELDS.filter((field) => flagged.has(field)),
    };
  });
  const model = payload.meta?.model ?? "unknown model";
  const seconds = payload.meta?.latency_ms ? ` in ${(payload.meta.latency_ms / 1000).toFixed(1)} s` : "";
  return resultSchema.parse({ records, source: `Read by the Digitali engine · ${model} on Nebius Token Factory${seconds}` });
}

export const extractAttendance = createServerFn({ method: "POST" })
  .inputValidator((input) => inputSchema.parse(input))
  .handler(async ({ data }) => {
    const engineUrl = process.env["ENGINE_URL"];
    if (engineUrl) {
      if (!data.dataUrl.startsWith(`data:${data.mimeType};base64,`)) {
        throw new Error("The uploaded photo format does not match its contents.");
      }
      return extractViaEngine(engineUrl, data, data.prompt);
    }

    const apiKey = process.env["NEBIUS_API_KEY"];
    if (!apiKey) throw new Error("The photo reader is not configured yet.");
    if (!data.dataUrl.startsWith(`data:${data.mimeType};base64,`)) {
      throw new Error("The uploaded photo format does not match its contents.");
    }

    const extractionRequest = data.prompt
      ? ` The user specifically wants: ${data.prompt}. Use this only to guide what you prioritize; do not invent values.`
      : "";

    const response = await fetch("https://api.tokenfactory.nebius.com/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "Qwen/Qwen2.5-VL-72B-Instruct",
        temperature: 0,
        messages: [
          {
            role: "user",
            content: [
              {
                type: "text",
                text: `Read this attendance sheet. Return every visible person as structured data. Use an empty string for missing text. Set signed to true only when a signature or clear mark is present. Put uncertain field names in lowConfidence. Never invent values.${extractionRequest}`,
              },
              { type: "image_url", image_url: { url: data.dataUrl } },
            ],
          },
        ],
        response_format: {
          type: "json_schema",
          json_schema: {
            name: "attendance_records",
            strict: true,
            schema: {
              type: "object",
              properties: {
                records: {
                  type: "array",
                  maxItems: 50,
                  items: {
                    type: "object",
                    properties: {
                      name: { type: "string" },
                      role: { type: "string" },
                      phone: { type: "string" },
                      signed: { type: "boolean" },
                      lowConfidence: {
                        type: "array",
                        items: { type: "string", enum: ["name", "role", "phone", "signed"] },
                      },
                    },
                    required: ["name", "role", "phone", "signed", "lowConfidence"],
                    additionalProperties: false,
                  },
                },
              },
              required: ["records"],
              additionalProperties: false,
            },
          },
        },
      }),
    });

    if (!response.ok) {
      const detail = await response.text();
      console.error(`Nebius request failed [${response.status}]: ${detail}`);
      throw new Error(`The photo could not be read (${response.status}). Please try again.`);
    }

    const payload = (await response.json()) as { choices?: Array<{ message?: { content?: string } }> };
    const content = payload.choices?.[0]?.message?.content;
    if (!content) throw new Error("The photo reader returned no records.");
    return resultSchema.parse({ ...JSON.parse(content), source: "Read directly by Qwen2.5-VL-72B on Nebius Token Factory" });
  });
