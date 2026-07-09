"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, Award, BidDraft, PriceLookup, Solicitation, SupplierMatch } from "@/lib/api";
import PriceAnalytics from "@/app/components/PriceAnalytics";

export default function SolicitationDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const solicitationId = Number(params.id);

  const [solicitation, setSolicitation] = useState<Solicitation | null>(null);
  const [matches, setMatches] = useState<SupplierMatch[]>([]);
  const [bidDrafts, setBidDrafts] = useState<BidDraft[]>([]);
  const [priceLookup, setPriceLookup] = useState<PriceLookup | null>(null);
  const [crawling, setCrawling] = useState(false);
  const [pricing, setPricing] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [benchmarkPrice, setBenchmarkPrice] = useState("");

  const load = async () => {
    const [sol, m, b] = await Promise.all([
      api.getSolicitation(solicitationId),
      api.getSolicitationMatches(solicitationId),
      api.getSolicitationBidDrafts(solicitationId),
    ]);
    setSolicitation(sol);
    setMatches(m);
    setBidDrafts(b);
    try {
      setPriceLookup(await api.getPriceLookup(solicitationId));
    } catch {
      setPriceLookup(null); // 404 = no lookup yet
    }
  };

  useEffect(() => {
    if (solicitationId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [solicitationId]);

  const findSuppliers = async () => {
    if (!solicitation?.nsn) {
      setStatusMsg("This solicitation has no NSN to search suppliers for.");
      return;
    }
    setCrawling(true);
    setStatusMsg("Submitting crawl job to agent…");
    try {
      const { job_id } = await api.createCrawlJob({
        type: "nsn_marketplace",
        params: { nsn: solicitation.nsn },
        solicitation_id: solicitationId,
      });

      const poll = async (): Promise<void> => {
        const job = await api.getCrawlJob(job_id);
        if (job.status === "done") {
          setStatusMsg("Supplier crawl complete.");
          await load();
        } else if (job.status === "error") {
          setStatusMsg(`Crawl failed: ${job.error}`);
        } else {
          setTimeout(poll, 2000);
        }
      };
      await poll();
    } catch (err) {
      setStatusMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setCrawling(false);
    }
  };

  const lookUpPrices = async () => {
    setPricing(true);
    setStatusMsg("Pulling historical award prices…");
    try {
      const { job_id } = await api.createCrawlJob({
        type: "price_history",
        params: solicitation?.nsn
          ? { nsn: solicitation.nsn }
          : { psc: (solicitation?.specs?.psc as string) ?? undefined },
        solicitation_id: solicitationId,
      });
      const poll = async (): Promise<void> => {
        const job = await api.getCrawlJob(job_id);
        if (job.status === "done") {
          setStatusMsg(null);
          await load();
        } else if (job.status === "error") {
          setStatusMsg(`Price lookup failed: ${job.error}`);
        } else {
          setTimeout(poll, 2000);
        }
      };
      await poll();
    } catch (err) {
      setStatusMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setPricing(false);
    }
  };

  const generateOutreach = async (matchId: number) => {
    await api.generateOutreach(matchId);
    router.push("/outreach");
  };

  const createBidDraft = async () => {
    try {
      await api.createBidDraft({
        solicitation_id: solicitationId,
        benchmark_award_price: benchmarkPrice ? Number(benchmarkPrice) : undefined,
      });
      await load();
    } catch (err) {
      setStatusMsg(err instanceof Error ? err.message : String(err));
    }
  };

  if (!solicitation) return <p className="text-sm text-neutral-400">Loading…</p>;

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs uppercase text-neutral-500">{solicitation.source}</span>
          <h1 className="text-xl font-semibold">{solicitation.title || solicitation.solicitation_id}</h1>
          {solicitation.is_sdvosb && (
            <span className="text-xs bg-emerald-900 text-emerald-300 px-2 py-0.5 rounded">SDVOSB</span>
          )}
          {solicitation.nmr_may_apply && (
            <span className="text-xs bg-amber-900 text-amber-300 px-2 py-0.5 rounded">
              NMR may apply — verify small-business manufacturer or waiver
            </span>
          )}
        </div>
        <p className="text-sm text-neutral-400 mt-1">{solicitation.description}</p>
        <div className="text-sm text-neutral-400 flex gap-4 mt-2">
          <span>NSN: {solicitation.nsn || "—"}</span>
          <span>Qty: {solicitation.qty ?? "—"}</span>
          <span>Set-aside: {solicitation.set_aside_type || "—"}</span>
          <span>
            Closes: {solicitation.close_date ? new Date(solicitation.close_date).toLocaleDateString() : "—"}
          </span>
          {solicitation.raw_url && (
            <a href={solicitation.raw_url} target="_blank" className="text-blue-400 underline">
              View original
            </a>
          )}
        </div>
        {solicitation.specs && Object.keys(solicitation.specs).length > 0 && (
          <div className="mt-3 border border-neutral-800 rounded p-3 text-sm">
            <p className="text-neutral-400 mb-1">Specs / dimensions</p>
            {Object.entries(solicitation.specs).map(([key, value]) => (
              <div key={key} className="flex gap-2">
                <span className="text-neutral-500">{key}:</span>
                <span>{String(value)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <section className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <h2 className="font-medium">Historical award prices</h2>
          <button
            onClick={lookUpPrices}
            disabled={pricing}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-3 py-1.5 rounded text-sm"
          >
            {pricing ? "Looking up…" : priceLookup ? "Refresh prices" : "Look up prices"}
          </button>
        </div>
        {priceLookup?.stats && priceLookup.stats.count > 0 ? (
          <PriceAnalytics
            stats={priceLookup.stats}
            awards={(priceLookup.awards as Award[]) ?? []}
            source={priceLookup.source}
          />
        ) : (
          <p className="text-sm text-neutral-500">
            {priceLookup
              ? "No past awards found for this item."
              : "No price history yet — click “Look up prices” to pull what the government paid before."}
          </p>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <h2 className="font-medium">Candidate suppliers</h2>
          <button
            onClick={findSuppliers}
            disabled={crawling}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-1.5 rounded text-sm"
          >
            {crawling ? "Searching…" : "Find suppliers for this NSN"}
          </button>
        </div>
        {statusMsg && <p className="text-sm text-neutral-400">{statusMsg}</p>}

        {Array.isArray(solicitation.specs?.part_numbers) &&
          (solicitation.specs.part_numbers as string[]).length > 0 && (
            <div className="border border-neutral-800 rounded p-3">
              <p className="text-xs text-neutral-400 mb-2">
                Manufacturer part numbers — quote these at a distributor by CAGE + part number:
              </p>
              <div className="flex flex-wrap gap-2">
                {(solicitation.specs.part_numbers as string[]).map((pn) => (
                  <span key={pn} className="text-xs bg-neutral-800 text-neutral-200 px-2 py-1 rounded font-mono">
                    {pn}
                  </span>
                ))}
              </div>
            </div>
          )}

        {matches.length === 0 && <p className="text-sm text-neutral-500">No suppliers matched yet.</p>}
        {matches.map((match) => (
          <div key={match.id} className="border border-neutral-800 rounded p-3 flex justify-between items-center">
            <div>
              <p className="font-medium">{match.supplier.name}</p>
              <p className="text-xs text-neutral-400">
                CAGE: {match.supplier.cage_code || "—"} · Price:{" "}
                {match.scraped_price ? `$${match.scraped_price.toFixed(2)}` : "—"} ·{" "}
                {match.supplier.url && (
                  <a href={match.supplier.url} target="_blank" className="text-blue-400 underline">
                    listing
                  </a>
                )}
              </p>
            </div>
            <button
              onClick={() => generateOutreach(match.id)}
              className="text-sm bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5 rounded"
            >
              Draft outreach email
            </button>
          </div>
        ))}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-medium">Bid drafts</h2>
        <div className="flex items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-neutral-400">Benchmark / last award price ($)</label>
            <input
              className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 w-48"
              value={benchmarkPrice}
              onChange={(e) => setBenchmarkPrice(e.target.value)}
              placeholder={
                priceLookup?.stats?.typical != null
                  ? `auto: $${priceLookup.stats.typical.toLocaleString()}`
                  : "optional"
              }
            />
          </div>
          <button
            onClick={createBidDraft}
            className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded text-sm"
          >
            Generate bid draft
          </button>
        </div>
        {bidDrafts.length === 0 && (
          <p className="text-sm text-neutral-500">
            No bid drafts yet. Add a priced supplier match first, then generate a draft.
          </p>
        )}
        {bidDrafts.map((draft) => (
          <div key={draft.id} className="border border-neutral-800 rounded p-3 text-sm">
            <p>Cost basis: ${draft.cost_basis?.toFixed(2)}</p>
            <p>
              Suggested markup: {((draft.suggested_markup_pct ?? 0) * 100).toFixed(1)}% → Suggested price: $
              {draft.suggested_price?.toFixed(2)}
            </p>
            {draft.benchmark_award_price && <p>Benchmark award price: ${draft.benchmark_award_price.toFixed(2)}</p>}
            <p className="text-neutral-400">Status: {draft.status}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
