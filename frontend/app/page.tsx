"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api, Solicitation } from "@/lib/api";

const SET_ASIDE_OPTIONS = [
  { value: "", label: "Any" },
  { value: "SDVOSB", label: "SDVOSB (veteran-owned)" },
  { value: "SBA", label: "Small Business" },
  { value: "WOSB", label: "WOSB" },
  { value: "HUBZONE", label: "HUBZone" },
  { value: "8A", label: "8(a)" },
];

const inputCls = "bg-neutral-900 border border-neutral-700 rounded px-2 py-1";
const labelCls = "text-xs text-neutral-400";

export default function SolicitationsPage() {
  // ---- Crawl panel state (what to pull from the live sites) ----
  const [crawlSetAside, setCrawlSetAside] = useState("");
  const [crawlPsc, setCrawlPsc] = useState("");
  const [crawlKeyword, setCrawlKeyword] = useState("");
  const [crawlNsn, setCrawlNsn] = useState("");
  const [crawling, setCrawling] = useState<"sam" | "dibbs" | null>(null);
  const [crawlMessage, setCrawlMessage] = useState<string | null>(null);
  const crawlStartRef = useRef<number>(0);

  // ---- Browse panel state (filter what's already in the local DB) ----
  const [browseSource, setBrowseSource] = useState("");
  const [browseNsn, setBrowseNsn] = useState("");
  const [browseSdvosbOnly, setBrowseSdvosbOnly] = useState(false);
  const [browseActiveOnly, setBrowseActiveOnly] = useState(true);
  const [solicitations, setSolicitations] = useState<Solicitation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSolicitations({
        source: browseSource || undefined,
        nsn: browseNsn || undefined,
        is_sdvosb: browseSdvosbOnly ? true : undefined,
        active_only: browseActiveOnly ? true : undefined,
      });
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
  }, [browseSource, browseNsn, browseSdvosbOnly, browseActiveOnly]);

  const runCrawl = async (type: "sam_search" | "dibbs_search") => {
    const source = type === "sam_search" ? "sam" : "dibbs";
    setCrawling(source);
    crawlStartRef.current = Date.now();
    setCrawlMessage(
      source === "dibbs"
        ? "Crawling DIBBS — a broad sweep takes ~30–60s, hang tight…"
        : "Crawling SAM.gov…"
    );
    try {
      const { job_id } = await api.createCrawlJob({
        type,
        params: {
          keyword: crawlKeyword || undefined,
          nsn: crawlNsn || undefined,
          classification_code: crawlPsc || undefined,
          set_aside_type: crawlSetAside || undefined,
        },
      });

      const poll = async (): Promise<void> => {
        const job = await api.getCrawlJob(job_id);
        const secs = Math.round((Date.now() - crawlStartRef.current) / 1000);
        if (job.status === "done") {
          const count = (job.result as { items?: unknown[] } | undefined)?.items?.length ?? 0;
          setCrawlMessage(`${source === "sam" ? "SAM.gov" : "DIBBS"} crawl finished in ${secs}s — ${count} solicitations pulled.`);
          setCrawling(null);
          await load();
        } else if (job.status === "error") {
          setCrawlMessage(`Crawl failed after ${secs}s: ${job.error}`);
          setCrawling(null);
        } else {
          setCrawlMessage(`Crawling ${source === "sam" ? "SAM.gov" : "DIBBS"}… ${secs}s elapsed`);
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
      {/* ---------- 1. PULL ---------- */}
      <section className="border border-neutral-800 rounded-lg p-4 flex flex-col gap-3">
        <div>
          <h2 className="font-medium">1. Pull new solicitations</h2>
          <p className="text-xs text-neutral-500">
            Crawls the live sites and saves what it finds locally. Leave everything blank for a
            broad &quot;what&apos;s out there&quot; sweep.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1">
            <label className={labelCls}>Set-aside <span className="text-neutral-600">(SAM.gov only)</span></label>
            <select className={inputCls} value={crawlSetAside} onChange={(e) => setCrawlSetAside(e.target.value)}>
              {SET_ASIDE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className={labelCls}>PSC / FSC <span className="text-neutral-600">(both sites; 53=hardware group, 5310=exact)</span></label>
            <input className={`${inputCls} w-36`} value={crawlPsc} onChange={(e) => setCrawlPsc(e.target.value)} placeholder="e.g. 53" list="psc-suggestions" />
            <datalist id="psc-suggestions">
              <option value="53">Hardware group (sweeps 5305-5365)</option>
              <option value="5310">Nuts & washers</option>
              <option value="5306">Bolts</option>
              <option value="31">Bearings group</option>
              <option value="59">Electrical group</option>
            </datalist>
          </div>
          <div className="flex flex-col gap-1">
            <label className={labelCls}>Keyword <span className="text-neutral-600">(SAM.gov only)</span></label>
            <input className={`${inputCls} w-36`} value={crawlKeyword} onChange={(e) => setCrawlKeyword(e.target.value)} placeholder="e.g. bracket" />
          </div>
          <div className="flex flex-col gap-1">
            <label className={labelCls}>Exact NSN <span className="text-neutral-600">(DIBBS only)</span></label>
            <input className={`${inputCls} w-44`} value={crawlNsn} onChange={(e) => setCrawlNsn(e.target.value)} placeholder="e.g. 5310-00-612-9969" />
          </div>
          <button
            onClick={() => runCrawl("dibbs_search")}
            disabled={crawling !== null}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-2 rounded text-sm"
          >
            {crawling === "dibbs" ? "Crawling…" : "Crawl DIBBS"}
          </button>
          <button
            onClick={() => runCrawl("sam_search")}
            disabled={crawling !== null}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-2 rounded text-sm"
          >
            {crawling === "sam" ? "Crawling…" : "Crawl SAM.gov"}
          </button>
        </div>
        {crawlMessage && <p className="text-sm text-neutral-400">{crawlMessage}</p>}
      </section>

      {/* ---------- 2. BROWSE ---------- */}
      <section className="border border-neutral-800 rounded-lg p-4 flex flex-col gap-3">
        <div>
          <h2 className="font-medium">2. Browse pulled solicitations ({solicitations.length})</h2>
          <p className="text-xs text-neutral-500">Filters what&apos;s already saved locally — doesn&apos;t touch the live sites.</p>
        </div>
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1">
            <label className={labelCls}>Source</label>
            <select className={inputCls} value={browseSource} onChange={(e) => setBrowseSource(e.target.value)}>
              <option value="">All</option>
              <option value="dibbs">DIBBS</option>
              <option value="sam">SAM.gov</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className={labelCls}>NSN contains</label>
            <input className={`${inputCls} w-36`} value={browseNsn} onChange={(e) => setBrowseNsn(e.target.value)} placeholder="e.g. 5310" />
          </div>
          <label className="flex items-center gap-2 text-sm pb-1">
            <input type="checkbox" checked={browseSdvosbOnly} onChange={(e) => setBrowseSdvosbOnly(e.target.checked)} />
            SDVOSB only
          </label>
          <label className="flex items-center gap-2 text-sm pb-1">
            <input type="checkbox" checked={browseActiveOnly} onChange={(e) => setBrowseActiveOnly(e.target.checked)} />
            Hide expired
          </label>
        </div>

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
                  <span className="text-xs bg-emerald-900 text-emerald-300 px-2 py-0.5 rounded">SDVOSB</span>
                )}
                {sol.set_aside_type && !sol.is_sdvosb && (
                  <span className="text-xs bg-neutral-800 text-neutral-300 px-2 py-0.5 rounded">{sol.set_aside_type}</span>
                )}
                {sol.nmr_may_apply && (
                  <span className="text-xs bg-amber-900 text-amber-300 px-2 py-0.5 rounded">NMR may apply</span>
                )}
              </div>
              <div className="text-sm text-neutral-400 flex gap-4">
                <span>NSN: {sol.nsn || "—"}</span>
                <span>Qty: {sol.qty ?? "—"}</span>
                <span>Closes: {sol.close_date ? new Date(sol.close_date).toLocaleDateString() : "—"}</span>
                <span className="text-neutral-600">{sol.solicitation_id}</span>
              </div>
            </Link>
          ))}
          {!loading && solicitations.length === 0 && (
            <p className="text-sm text-neutral-500">Nothing saved yet — run a crawl above.</p>
          )}
        </div>
      </section>
    </div>
  );
}
