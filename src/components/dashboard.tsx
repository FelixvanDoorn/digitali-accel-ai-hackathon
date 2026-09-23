import { useMemo, useState, type ReactNode } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getDashboard, type Dashboard as DashboardData } from "@/lib/dashboard.functions";

// Marks use a more saturated step of the brand green (--mwani reads gray at mark size); "needs a check"
// uses --manjano as a warning status, always with an icon and a visible value. Checked with the dataviz
// palette validator against the --chokaa surface.
const MARK = "#2F7A4C";
const MARK_TRACK = "#D5E5DA";
const WARN = "#E0A62B";
const GRID = "#E3D8C6";
const INK_MUTED = "#6A5F55";

const PERIODS = [
  { days: 7, label: "Last 7 days" },
  { days: 30, label: "Last 30 days" },
  { days: 90, label: "Last 90 days" },
  { days: 0, label: "All time" },
];

const number = new Intl.NumberFormat("en");
const percent = (part: number, whole: number) => (whole ? Math.round((part / whole) * 100) : 0);

function label(field: string) {
  return field.charAt(0).toUpperCase() + field.slice(1).replace(/_/g, " ");
}

export function Dashboard() {
  const [templateId, setTemplateId] = useState("attendance");
  const [days, setDays] = useState(30);
  const query = useQuery({
    queryKey: ["dashboard", templateId, days],
    queryFn: () => getDashboard({ data: { templateId, days } }),
    placeholderData: keepPreviousData,
  });
  const data = query.data;

  return (
    <div className="mx-auto w-full max-w-[1280px] px-4 py-10 sm:px-5 md:py-14">
      <header className="mb-8">
        <p className="eyebrow">Operational insights</p>
        <h1 className="font-display text-4xl md:text-5xl">{data?.template.name ?? "Dashboard"}</h1>
        <p className="mt-3 max-w-2xl text-[#6A5F55]">
          Everything read from paper so far, straight from the database. Each photo sent through the
          demo adds to it.
        </p>
      </header>

      {/* Filters: one row above everything they scope. */}
      <div className="mb-8 flex flex-wrap items-center gap-3" role="group" aria-label="Filters">
        <select
          aria-label="Form type"
          className="h-10 border border-hairline bg-chokaa px-3 text-sm"
          value={templateId}
          onChange={(event) => setTemplateId(event.target.value)}
        >
          {(data?.templates ?? [{ id: "attendance", name: "Attendance sheet" }]).map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <div
          className="flex flex-wrap border border-hairline"
          role="radiogroup"
          aria-label="Time range"
        >
          {PERIODS.map((p) => (
            <button
              key={p.days}
              type="button"
              role="radio"
              aria-checked={days === p.days}
              onClick={() => setDays(p.days)}
              className={`h-10 px-3 text-sm ${days === p.days ? "bg-mkaa font-semibold text-chokaa" : "hover:bg-[#EDE4D4]"}`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {query.isError && <p className="demo-error mb-6">{(query.error as Error).message}</p>}
      {!data && query.isPending && <p className="text-[#6A5F55]">Loading…</p>}

      {data && (
        // Refetching keeps the previous render, dimmed, instead of flashing a skeleton.
        <div
          className={`transition-opacity ${query.isFetching ? "opacity-60" : ""}`}
          aria-busy={query.isFetching}
        >
          {data.totals.uploads === 0 ? <EmptyState /> : <Insights data={data} />}
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="border border-hairline p-10 text-center">
      <p className="font-display text-2xl">No uploads in this period yet</p>
      <p className="mt-2 text-[#6A5F55]">
        Send a photo through the{" "}
        <a className="underline" href="/#demo">
          demo
        </a>{" "}
        and it shows up here.
      </p>
    </div>
  );
}

function Insights({ data }: { data: DashboardData }) {
  const fieldStats = new Map(data.fields.map((f) => [f.field, f]));
  const fields = data.template.fields.map((f) => ({ ...f, stats: fieldStats.get(f.name) }));
  const cells = data.totals.records * Math.max(fields.length, 1);
  const booleans = fields.filter((f) => f.type === "boolean" && f.stats);
  const categories = fields.filter((f) => f.stats && f.stats.top.length > 0);

  return (
    <div className="grid gap-6">
      <div className="grid grid-cols-2 gap-px border border-hairline bg-hairline lg:grid-cols-4">
        <StatTile label="Uploads" value={number.format(data.totals.uploads)} />
        <StatTile label="Records read" value={number.format(data.totals.records)} />
        <StatTile
          label="Fields needing a check"
          value={`${percent(data.totals.flags, cells)}%`}
          note={`${number.format(data.totals.flags)} of ${number.format(cells)}`}
        />
        <StatTile
          label="Average reading time"
          value={`${(data.totals.avg_latency_ms / 1000).toFixed(1)} s`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Uploads per day" subtitle="Photos sent, per day (UTC)">
          <UploadsPerDay data={data} />
        </Card>

        {booleans.length > 0 && (
          <Card title="Yes / no fields" subtitle="Share of records marked yes">
            <div className="grid gap-5">
              {booleans.map((f) => {
                const s = f.stats!;
                const answered = s.true + s.false;
                return (
                  <Meter
                    key={f.name}
                    label={label(f.name)}
                    value={percent(s.true, answered)}
                    detail={`${number.format(s.true)} of ${number.format(answered)} yes`}
                  />
                );
              })}
            </div>
          </Card>
        )}

        <Card
          title="Fields needing a check"
          subtitle="Share of records where the field couldn't be read"
          icon={
            <AlertTriangle aria-hidden="true" className="size-4" style={{ color: "#9A6B0B" }} />
          }
        >
          <HorizontalBars
            color={WARN}
            unit="%"
            rows={fields.map((f) => ({
              name: label(f.name),
              value: percent(f.stats?.flagged ?? 0, f.stats?.records ?? 0),
              detail: `${number.format(f.stats?.flagged ?? 0)} of ${number.format(f.stats?.records ?? 0)} records`,
            }))}
          />
        </Card>

        {categories.map((f) => (
          <Card key={f.name} title={`Most common ${f.name}`} subtitle="Records per value">
            <HorizontalBars
              color={MARK}
              rows={f.stats!.top.map((t) => ({
                name: t.value,
                value: t.count,
                detail: "",
              }))}
            />
          </Card>
        ))}
      </div>

      <Card title="Latest uploads">
        <RecentUploads data={data} />
      </Card>
    </div>
  );
}

function StatTile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="bg-chokaa p-5">
      <p className="text-sm text-[#6A5F55]">{label}</p>
      <p className="mt-2 font-sans text-3xl font-semibold md:text-4xl">{value}</p>
      {note && <p className="mt-1 text-xs text-[#6A5F55]">{note}</p>}
    </div>
  );
}

function Card({
  title,
  subtitle,
  icon,
  children,
}: {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="border border-hairline p-5 md:p-6">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        {icon}
        {title}
      </h2>
      {subtitle && <p className="mb-4 text-sm text-[#6A5F55]">{subtitle}</p>}
      {children}
    </section>
  );
}

// Tooltip: value first and strong, label second.
type TooltipData = {
  active?: boolean | undefined;
  payload?: ReadonlyArray<{ value?: unknown; payload?: unknown }> | undefined;
  label?: unknown;
};

function ChartTooltip({
  active,
  payload,
  label: name,
  unit = "",
  detail,
}: TooltipData & { unit?: string; detail?: string }) {
  const first = payload?.[0];
  if (!active || !first) return null;
  const row = (first.payload ?? {}) as { name?: string; detail?: string };
  return (
    <div className="border border-hairline bg-chokaa px-3 py-2 text-sm shadow-sm">
      <p className="font-semibold">
        {number.format(Number(first.value ?? 0))}
        {unit}
      </p>
      <p className="text-[#6A5F55]">{row.name ?? detail ?? String(name ?? "")}</p>
      {row.detail && <p className="text-[#6A5F55]">{row.detail}</p>}
    </div>
  );
}

function UploadsPerDay({ data }: { data: DashboardData }) {
  // Fill in days without uploads so gaps show as gaps (only for bounded ranges).
  const rows = useMemo(() => {
    const byDay = new Map(data.per_day.map((d) => [d.day, d.uploads]));
    if (!data.days || data.days > 90)
      return data.per_day.map((d) => ({ day: d.day, uploads: d.uploads }));
    const out: Array<{ day: string; uploads: number }> = [];
    const today = new Date();
    for (let i = data.days - 1; i >= 0; i--) {
      const d = new Date(
        Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate() - i),
      );
      const key = d.toISOString().slice(0, 10);
      out.push({ day: key, uploads: byDay.get(key) ?? 0 });
    }
    return out;
  }, [data]);
  const short = (day: string) =>
    new Date(`${day}T00:00:00Z`).toLocaleDateString("en", {
      day: "numeric",
      month: "short",
      timeZone: "UTC",
    });

  return (
    <>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 4, left: -20, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke={GRID} />
            <XAxis
              dataKey="day"
              tickFormatter={short}
              tick={{ fill: INK_MUTED, fontSize: 12 }}
              axisLine={{ stroke: GRID }}
              tickLine={false}
              minTickGap={24}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: INK_MUTED, fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: "#EDE4D4" }}
              content={({ active, payload, label: day }) => (
                <ChartTooltip
                  active={active}
                  payload={payload}
                  detail={day ? short(String(day)) : ""}
                />
              )}
            />
            <Bar
              isAnimationActive={false}
              dataKey="uploads"
              name="Uploads"
              fill={MARK}
              radius={[4, 4, 0, 0]}
              maxBarSize={24}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <DataTable
        columns={["Day", "Uploads"]}
        rows={rows
          .filter((r) => r.uploads > 0)
          .map((r) => [short(r.day), number.format(r.uploads)])}
      />
    </>
  );
}

function Meter({ label: name, value, detail }: { label: string; value: number; detail: string }) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <span className="flex items-center gap-2 font-medium">
          <CheckCircle2 aria-hidden="true" className="size-4" style={{ color: MARK }} />
          {name}
        </span>
        <span className="text-sm">
          <strong className="text-base">{value}%</strong>{" "}
          <span className="text-[#6A5F55]">· {detail}</span>
        </span>
      </div>
      <div
        className="h-3 w-full rounded-full"
        style={{ background: MARK_TRACK }}
        role="meter"
        aria-label={name}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="h-3 rounded-full" style={{ width: `${value}%`, background: MARK }} />
      </div>
    </div>
  );
}

function HorizontalBars({
  rows,
  color,
  unit = "",
}: {
  rows: Array<{ name: string; value: number; detail: string }>;
  color: string;
  unit?: string;
}) {
  return (
    <>
      <div style={{ height: Math.max(rows.length * 40 + 16, 80) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 0, right: 48, left: 0, bottom: 0 }}
          >
            <XAxis type="number" hide domain={[0, unit === "%" ? 100 : "dataMax"]} />
            <YAxis
              type="category"
              dataKey="name"
              width={110}
              tick={{ fill: "#2B2622", fontSize: 13 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: "#EDE4D4" }}
              content={({ active, payload, label: name }) => (
                <ChartTooltip active={active} payload={payload} label={name} unit={unit} />
              )}
            />
            <Bar
              isAnimationActive={false}
              dataKey="value"
              fill={color}
              radius={[0, 4, 4, 0]}
              maxBarSize={24}
            >
              {/* Values ride the bar tip, in ink, so the low-contrast warning hue never carries them alone. */}
              <LabelList
                dataKey="value"
                position="right"
                formatter={(v: number) => `${number.format(v)}${unit}`}
                style={{ fill: "#2B2622", fontSize: 13, fontWeight: 600 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <DataTable
        columns={["", "Value", ""]}
        rows={rows.map((r) => [r.name, `${number.format(r.value)}${unit}`, r.detail])}
      />
    </>
  );
}

function DataTable({ columns, rows }: { columns: string[]; rows: string[][] }) {
  if (!rows.length) return null;
  return (
    <details className="mt-3 text-sm">
      <summary className="cursor-pointer text-[#6A5F55]">Show as table</summary>
      <table className="mt-2 w-full text-left tabular-nums">
        <thead>
          <tr className="border-b border-hairline text-[#6A5F55]">
            {columns.map((c, i) => (
              <th key={i} className="py-1 pr-3 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-hairline">
              {row.map((cell, j) => (
                <td key={j} className="py-1 pr-3">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

function RecentUploads({ data }: { data: DashboardData }) {
  const time = (iso: string) =>
    new Date(iso).toLocaleString("en", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-hairline text-[#6A5F55]">
            <th className="py-2 pr-3 font-medium">When</th>
            <th className="py-2 pr-3 font-medium">Source</th>
            <th className="py-2 pr-3 font-medium">Note</th>
            <th className="py-2 pr-3 text-right font-medium">Records</th>
            <th className="py-2 pr-3 text-right font-medium">To check</th>
            <th className="py-2 pr-3 text-right font-medium">Reading time</th>
            <th className="py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="tabular-nums">
          {data.recent.map((u) => (
            <tr key={u.id} className="border-b border-hairline">
              <td className="py-2 pr-3 whitespace-nowrap">{time(u.created_at)}</td>
              <td className="py-2 pr-3">{u.source === "web" ? "Website" : "API"}</td>
              <td
                className="max-w-[260px] truncate py-2 pr-3 text-[#6A5F55]"
                title={u.instructions ?? ""}
              >
                {u.instructions ?? "—"}
              </td>
              <td className="py-2 pr-3 text-right">{u.record_count}</td>
              <td className="py-2 pr-3 text-right">
                {u.flag_count > 0 ? (
                  <span className="inline-flex items-center gap-1">
                    <AlertTriangle
                      aria-hidden="true"
                      className="size-3.5"
                      style={{ color: "#9A6B0B" }}
                    />
                    {u.flag_count}
                  </span>
                ) : (
                  0
                )}
              </td>
              <td className="py-2 pr-3 text-right">{(u.latency_ms / 1000).toFixed(1)} s</td>
              <td className="py-2">{u.status === "confirmed" ? "Confirmed" : "Not yet checked"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
