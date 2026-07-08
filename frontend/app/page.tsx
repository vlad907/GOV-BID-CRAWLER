"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Solicitation, SolicitationFilters } from "@/lib/api";

const SET_ASIDE_OPTIONS = [
  { value: "", label: "Any set-aside" },
  { value: "SDVOSB", label: "SDVOSB" },
  { value: "SBA", label: "Small Business" },
  { value: "WOSB", label: "WOSB" },
  { value: "HUBZONE", label: "HUBZone" },
  { value: "8A", label: "8(a)" },
];

export default function SolicitationsPage() {
  const [filters, setFilters] = useState<SolicitationFilters>({});
  const [solicitations, setSolicitations] = useState<Solicitation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [crawling, setCrawling] = useState<"sam" | "dibbs" | null>(null);
  const [crawlMessage, setCrawlMessage] = useState<string | null>(null);
  const [naicsCode, setNaicsCode] = useState("");
  const [pscCode, setPscCode] = useState("");
  const [keyword, setKeyword] = useState("");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSolicitations(filters);
      setSolicitations(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.source, filters.set_aside_type, filters.is_sdvosb, filters.nsn]);

  const runCrawl = async (type: "sam_search" | "dibbs_search") => {
    const source = type === "sam_search" ? "sam" : "dibbs";
    setCrawling(source);
    setCrawlMessage("Submitting crawl job to agent — watch for a real Chrome window there…");
    try {
      const { job_id } = await api.createCrawlJob({
        type,
        params: {
          keyword: keyword || filters.nsn || undefined,
          naics_code: naicsCode || undefined,
          classification_code: pscCode || undefined,
          set_aside_type: filters.set_aside_type,
        },
      });

      const poll = async (): Promise<void> => {
        const job = await api.getCrawlJob(job_id);
        if (job.status === "done") {
          setCrawlMessage("Crawl complete.");
          setCrawling(null);
          await load();
        } else if (job.status === "error") {
          setCrawlMessage(`Crawl failed: ${job.error}`);
          setCrawling(null);
        } else {
          setTimeout(poll, 2000);
        }
      };
      await poll();
    } catch (err) {
      setCrawlMessage(err instanceof Error ? err.message : String(err));
      setCrawling(null);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end gap-4 border border-neutral-800 rounded-lg p-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-400">Set-aside</label>
          <select
            className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1"
            value={filters.set_aside_type ?? ""}
            onChange={(e) =>
              setFilters((f) => ({ ...f, set_aside_type: e.target.value || undefined }))
            }
          >
            {SET_ASIDE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-400">Source</label>
          <select
            className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1"
            value={filters.source ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, source: e.target.value || undefined }))}
          >
            <option value="">All sources</option>
            <option value="sam">SAM.gov</option>
            <option value="dibbs">DIBBS</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-400">NSN contains</label>
          <input
            className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1"
            value={filters.nsn ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, nsn: e.target.value || undefined }))}
            placeholder="e.g. 5310"
          />
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={!!filters.is_sdvosb}
            onChange={(e) =>
              setFilters((f) => ({ ...f, is_sdvosb: e.target.checked ? true : undefined }))
            }
          />
          SDVOSB only (veteran-owned)
        </label>
      </div>

      <div className="flex flex-wrap items-end gap-4 border border-neutral-800 rounded-lg p-4">
        <p className="w-full text-xs text-neutral-500">
          Crawl the real sites directly — no account or API key needed. Results land in the list
          below for you to sift through.
        </p>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-400">Keyword</label>
          <input
            className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 w-40"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="e.g. bracket"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-400">
            PSC / FSC code (what&apos;s being bought — the &quot;parts only&quot; filter)
          </label>
          <input
            className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 w-40"
            value={pscCode}
            onChange={(e) => setPscCode(e.target.value)}
            placeholder="e.g. 53 = Hardware"
            list="psc-suggestions"
          />
          <datalist id="psc-suggestions">
            <option value="53">Hardware & Abrasives</option>
            <option value="59">Electrical/Electronic Components</option>
            <option value="31">Bearings</option>
            <option value="34">Metalworking Machinery</option>
            <option value="29">Engine Accessories</option>
            <option value="61">Electric Wire & Cable</option>
            <option value="47">Pipe, Tubing, Hose & Fittings</option>
          </datalist>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-400">NAICS code (SAM.gov only, optional)</label>
          <input
            className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 w-32"
            value={naicsCode}
            onChange={(e) => setNaicsCode(e.target.value)}
            placeholder="e.g. 332999"
          />
        </div>

        <button
          onClick={() => runCrawl("sam_search")}
          disabled={crawling !== null}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-2 rounded text-sm"
        >
          {crawling === "sam" ? "Crawling…" : "Crawl SAM.gov"}
        </button>
        <button
          onClick={() => runCrawl("dibbs_search")}
          disabled={crawling !== null}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-2 rounded text-sm"
        >
          {crawling === "dibbs" ? "Crawling…" : "Crawl DIBBS"}
        </button>
      </div>

      {crawlMessage && <p className="text-sm text-neutral-400">{crawlMessage}</p>}
      {error && <p className="text-sm text-red-400">{error}</p>}
      {loading && <p className="text-sm text-neutral-400">Loading…</p>}

      <div className="flex flex-col gap-2">
        {solicitations.map((sol) => (
          <Link
            key={sol.id}
            href={`/solicitations/${sol.id}`}
            className="border border-neutral-800 rounded-lg p-4 hover:border-neutral-600 flex flex-col gap-1"
          >
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs uppercase text-neutral-500">{sol.source}</span>
              <span className="font-medium">{sol.title || sol.solicitation_id}</span>
              {sol.is_sdvosb && (
                <span className="text-xs bg-emerald-900 text-emerald-300 px-2 py-0.5 rounded">
                  SDVOSB
                </span>
              )}
              {sol.set_aside_type && !sol.is_sdvosb && (
                <span className="text-xs bg-neutral-800 text-neutral-300 px-2 py-0.5 rounded">
                  {sol.set_aside_type}
                </span>
              )}
              {sol.nmr_may_apply && (
                <span className="text-xs bg-amber-900 text-amber-300 px-2 py-0.5 rounded">
                  NMR may apply
                </span>
              )}
            </div>
            <div className="text-sm text-neutral-400 flex gap-4">
              <span>NSN: {sol.nsn || "—"}</span>
              <span>Qty: {sol.qty ?? "—"}</span>
              <span>Closes: {sol.close_date ? new Date(sol.close_date).toLocaleDateString() : "—"}</span>
            </div>
          </Link>
        ))}
        {!loading && solicitations.length === 0 && (
          <p className="text-sm text-neutral-500">
            No solicitations yet. Crawl SAM.gov or DIBBS above (needs the crawler agent running).
          </p>
        )}
      </div>
    </div>
  );
}
