"use client";

import { useEffect, useState } from "react";
import { api, OutreachDraft } from "@/lib/api";

export default function OutreachPage() {
  const [drafts, setDrafts] = useState<OutreachDraft[]>([]);
  const [editing, setEditing] = useState<Record<number, { subject: string; body: string }>>({});

  const load = async () => {
    const data = await api.listOutreachDrafts();
    setDrafts(data);
    setEditing(
      Object.fromEntries(
        data.map((d) => [d.id, { subject: d.draft_subject, body: d.draft_body }])
      )
    );
  };

  useEffect(() => {
    load();
  }, []);

  const save = async (id: number) => {
    const edit = editing[id];
    await api.updateOutreachDraft(id, { draft_subject: edit.subject, draft_body: edit.body });
    await load();
  };

  const markSent = async (id: number) => {
    await api.updateOutreachDraft(id, { status: "sent" });
    await load();
  };

  return (
    <div className="flex flex-col gap-4 max-w-3xl">
      <h1 className="text-xl font-semibold">Outreach drafts</h1>
      <p className="text-sm text-neutral-400">
        Drafts are never sent automatically — review and send manually, then mark as sent.
      </p>
      {drafts.length === 0 && (
        <p className="text-sm text-neutral-500">
          No drafts yet. Generate one from a supplier match on a solicitation page.
        </p>
      )}
      {drafts.map((draft) => (
        <div key={draft.id} className="border border-neutral-800 rounded p-4 flex flex-col gap-2">
          <div className="flex justify-between items-center">
            <span className="text-xs uppercase text-neutral-500">Status: {draft.status}</span>
            {draft.status === "draft" && (
              <button
                onClick={() => markSent(draft.id)}
                className="text-xs bg-emerald-900 hover:bg-emerald-800 text-emerald-300 px-2 py-1 rounded"
              >
                Mark sent
              </button>
            )}
          </div>
          <input
            className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1"
            value={editing[draft.id]?.subject ?? ""}
            onChange={(e) =>
              setEditing((prev) => ({
                ...prev,
                [draft.id]: { ...prev[draft.id], subject: e.target.value },
              }))
            }
          />
          <textarea
            className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 h-40 font-mono text-sm"
            value={editing[draft.id]?.body ?? ""}
            onChange={(e) =>
              setEditing((prev) => ({
                ...prev,
                [draft.id]: { ...prev[draft.id], body: e.target.value },
              }))
            }
          />
          <button
            onClick={() => save(draft.id)}
            className="self-start text-sm bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5 rounded"
          >
            Save edits
          </button>
        </div>
      ))}
    </div>
  );
}
