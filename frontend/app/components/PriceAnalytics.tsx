"use client";

import { Award, PriceStats } from "@/lib/api";

function StatCard({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div
      className={`flex flex-col gap-1 rounded-lg border px-4 py-3 ${
        accent
          ? "border-indigo-700 bg-indigo-950/40"
          : "border-neutral-800 bg-neutral-900/40"
      }`}
    >
      <span className="text-[11px] uppercase tracking-wide text-neutral-500">{label}</span>
      <span className={`text-lg font-semibold font-mono ${accent ? "text-indigo-300" : "text-neutral-100"}`}>
        {value}
      </span>
    </div>
  );
}

function money(n: number | null | undefined): string {
  if (n == null) return "—";
  return `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** Dependency-free SVG bar chart of award prices over time (oldest → newest). */
function PriceBars({ awards }: { awards: Award[] }) {
  const points = awards
    .filter((a) => a.price != null)
    .slice()
    .reverse(); // API gives newest-first; chart reads left→right oldest→newest
  if (points.length < 2) return null;

  const prices = points.map((p) => p.price as number);
  const max = Math.max(...prices);
  const min = Math.min(...prices);
  const range = max - min || 1;
  const W = 520;
  const H = 120;
  const pad = 8;
  const barW = (W - pad * 2) / points.length;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-32">
      {points.map((p, i) => {
        const v = p.price as number;
        const h = 12 + ((v - min) / range) * (H - 28);
        return (
          <g key={i}>
            <rect
              x={pad + i * barW + barW * 0.15}
              y={H - h}
              width={barW * 0.7}
              height={h}
              rx={2}
              className="fill-indigo-500/70"
            >
              <title>
                {p.award_date ?? "?"} · {money(v)}
                {p.awardee_cage ? ` · CAGE ${p.awardee_cage}` : ""}
              </title>
            </rect>
          </g>
        );
      })}
    </svg>
  );
}

export default function PriceAnalytics({
  stats,
  awards,
  source,
}: {
  stats: PriceStats;
  awards: Award[];
  source?: string | null;
}) {
  const isUsa = source === "usaspending";
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        <StatCard label="Last award" value={money(stats.last)} accent />
        <StatCard label="Average" value={money(stats.avg)} />
        <StatCard label="Median" value={money(stats.median)} />
        <StatCard label="Low" value={money(stats.low)} />
        <StatCard label="High" value={money(stats.high)} />
      </div>

      <PriceBars awards={awards} />

      <div className="text-xs text-neutral-500">
        {stats.count} award{stats.count === 1 ? "" : "s"} ·{" "}
        {isUsa
          ? "Source: USASpending.gov (PSC-level contract totals — coarse, not unit prices)"
          : "Source: DLA award history (per-NSN)"}
      </div>

      {awards.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-neutral-800">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-neutral-500 border-b border-neutral-800">
              <tr>
                <th className="px-3 py-2 font-medium">Award date</th>
                <th className="px-3 py-2 font-medium">{isUsa ? "Awardee" : "Awardee CAGE"}</th>
                <th className="px-3 py-2 font-medium text-right">Price</th>
                <th className="px-3 py-2 font-medium">Award #</th>
              </tr>
            </thead>
            <tbody>
              {awards.map((a, i) => (
                <tr key={i} className="border-b border-neutral-900 last:border-0">
                  <td className="px-3 py-2 text-neutral-300">{a.award_date ?? "—"}</td>
                  <td className="px-3 py-2 text-neutral-300 font-mono text-xs">
                    {a.awardee_name ?? a.awardee_cage ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-indigo-300">{money(a.price)}</td>
                  <td className="px-3 py-2 text-neutral-500 font-mono text-xs">{a.award_number ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
