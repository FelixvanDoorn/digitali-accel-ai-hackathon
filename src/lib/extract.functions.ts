import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

const inputSchema = z.object({
  dataUrl: z.string().max(9_500_000),
  mimeType: z.enum(["image/jpeg", "image/png", "image/webp"]),
});

const recordSchema = z.object({
  name: z.string(),
  role: z.string(),
  phone: z.string(),
  signed: z.boolean(),
  lowConfidence: z.array(z.enum(["name", "role", "phone", "signed"])),
});

const resultSchema = z.object({ records: z.array(recordSchema).max(50) });

export type ExtractedRecord = z.infer<typeof recordSchema>;

export const extractAttendance = createServerFn({ method: "POST" })
  .inputValidator((input) => inputSchema.parse(input))
  .handler(async ({ data }) => {
    const apiKey = process.env["NEBIUS_API_KEY"];
    if (!apiKey) throw new Error("The photo reader is not configured yet.");
    if (!data.dataUrl.startsWith(`data:${data.mimeType};base64,`)) {
      throw new Error("The uploaded photo format does not match its contents.");
    }

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
                text: "Read this attendance sheet. Return every visible person as structured data. Use an empty string for missing text. Set signed to true only when a signature or clear mark is present. Put uncertain field names in lowConfidence. Never invent values.",
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
    return resultSchema.parse(JSON.parse(content));
  });
