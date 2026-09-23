import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

const inputSchema = z.object({
  templateId: z
    .string()
    .regex(/^[a-z0-9-]+$/)
    .max(64),
  days: z.number().int().min(0).max(3650),
});

// Response of the engine's GET /dashboard (engine/app/main.py, db/migrations/002_dashboard.sql).
export type DashboardField = {
  field: string;
  records: number;
  empty: number;
  flagged: number;
  true: number;
  false: number;
  distinct: number;
  top: Array<{ value: string; count: number }>;
};

export type Dashboard = {
  template: {
    id: string;
    name: string;
    fields: Array<{ name: string; type: string; hint: string }>;
  };
  templates: Array<{ id: string; name: string }>;
  days: number;
  since: string;
  totals: {
    uploads: number;
    records: number;
    flags: number;
    confirmed: number;
    avg_latency_ms: number;
  };
  per_day: Array<{ day: string; uploads: number; records: number }>;
  fields: DashboardField[];
  recent: Array<{
    id: string;
    created_at: string;
    source: string;
    instructions: string | null;
    record_count: number;
    flag_count: number;
    latency_ms: number;
    model: string;
    status: string;
  }>;
};

export const getDashboard = createServerFn({ method: "GET" })
  .inputValidator((input) => inputSchema.parse(input))
  .handler(async ({ data }): Promise<Dashboard> => {
    const engineUrl = process.env["ENGINE_URL"];
    if (!engineUrl) throw new Error("The dashboard is not configured yet.");

    const headers: Record<string, string> = {};
    const key = process.env["ENGINE_API_KEY"];
    if (key) headers["x-api-key"] = key;

    const url = new URL(`${engineUrl.replace(/\/$/, "")}/dashboard`);
    url.searchParams.set("template_id", data.templateId);
    url.searchParams.set("days", String(data.days));

    let response: Response;
    try {
      response = await fetch(url, { headers, signal: AbortSignal.timeout(20_000) });
    } catch (caught) {
      console.error("Dashboard request failed:", caught);
      throw new Error("The dashboard is offline right now. Please try again later.");
    }
    if (!response.ok) {
      console.error(`Dashboard request failed [${response.status}]: ${await response.text()}`);
      throw new Error(
        response.status === 503
          ? "The database is not configured yet."
          : `The dashboard could not be loaded (${response.status}).`,
      );
    }
    return (await response.json()) as Dashboard;
  });
