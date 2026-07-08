"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, BidDraft } from "@/lib/api";

export default function BidsPage() {
  const [drafts, setDrafts] = useState<BidDraft[]>([]);

  const load = async () => {
    setDrafts(await api.listBidDrafts());
  };

  useEffect(() => {
    load();
  }, []);

  const markSubmitted = async (id: number) => {
    await api.updateBidDraft(id, { status: "submitted" });
    await load();
  };

  return (
    <div className="flex flex-col gap-4 max-w-3xl">
      <h1 className="text-xl font-semibold">Bid drafts</h1>
      <p className="text-sm text-neutral-400">
        Bids are never submitted automatically — review pricing and compliance (NMR, TAA, country
        of origin) before submitting manually in DIBBS/SAM.gov, then mark as submitted here.
      </p>
      {drafts.length === 0 && <p className="text-sm text-neutral-500">No bid drafts yet.</p>}
      {drafts.map((draft) => (
        <div key={draft.id} className="border border-neutral-800 rounded p-4 flex flex-col gap-1 text-sm">
          <div className="flex justify-between items-center">
            <Link href={`/solicitations/${draft.solicitation_id}`} className="text-blue-400 underline">
              Solicitation #{draft.solicitation_id}
            </Link>
            <span className="text-xs uppercase text-neutral-500">Status: {draft.status}</span>
          </div>
          <p>Cost basis: ${draft.cost_basis?.toFixed(2)}</p>
          <p>
            Suggested markup: {((draft.suggested_markup_pct ?? 0) * 100).toFixed(1)}% → Suggested price: $
            {draft.suggested_price?.toFixed(2)}
          </p>
          {draft.benchmark_award_price && (
            <p>Benchmark award price: ${draft.benchmark_award_price.toFixed(2)}</p>
          )}
          {draft.status === "draft" && (
            <button
              onClick={() => markSubmitted(draft.id)}
              className="self-start mt-1 text-xs bg-emerald-900 hover:bg-emerald-800 text-emerald-300 px-2 py-1 rounded"
            >
              Mark submitted
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
