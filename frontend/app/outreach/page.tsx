"use client";

import { useEffect, useState } from "react";
import { api, OutreachDraft } from "@/lib/api";

type EditState = { to: string; subject: string; body: string };

export default function OutreachPage() {
  const [drafts, setDrafts] = useState<OutreachDraft[]>([]);
  const [editing, setEditing] = useState<Record<number, EditState>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    const data = await api.listOutreachDrafts();
    setDrafts(data);
    setEditing(
      Object.fromEntries(
        data.map((d) => [
          d.id,
          { to: d.recipient_email ?? "", subject: d.draft_subject, body: d.draft_body },
        ])
      )
    );
  };

  useEffect(() => {
    load();
  }, []);

  const patch = (id: number, key: keyof EditState, value: string) =>
    setEditing((prev) => ({ ...prev, [id]: { ...prev[id], [key]: value } }));

  const save = async (id: number) => {
    const e = editing[id];
    await api.updateOutreachDraft(id, {
      recipient_email: e.to,
      draft_subject: e.subject,
      draft_body: e.body,
    });
    setMessage("Saved.");
    await load();
  };

  const send = async (id: number) => {
    const e = editing[id];
    if (!e.to) {
      setMessage("Enter a recipient email first.");
      return;
    }
    setBusy(id);
    setMessage(null);
    try {
      // persist edits (incl. recipient) before sending
      await api.updateOutreachDraft(id, {
        recipient_email: e.to,
        draft_subject: e.subject,
        draft_body: e.body,
      });
      await api.sendOutreachDraft(id);
      setMessage(`Sent to ${e.to}.`);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  };

  const syncReplies = async () => {
    setSyncing(true);
    setMessage(null);
    try {
      const res = await api.syncReplies();
      setMessage(res.detail ?? `Pulled ${res.new_replies} new repl${res.new_replies === 1 ? "y" : "ies"}.`);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 max-w-3xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Outreach</h1>
          <p className="text-sm text-neutral-400">
            Nothing sends until you click Send on a draft. Replies are pulled from your inbox and a
            quoted price is auto-extracted.
          </p>
        </div>
        <button
          onClick={syncReplies}
          disabled={syncing}
          className="shrink-0 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white px-3 py-2 rounded text-sm"
        >
          {syncing ? "Syncing…" : "Sync replies"}
        </button>
      </div>
      {message && <p className="text-sm text-neutral-400">{message}</p>}

      {drafts.length === 0 && (
        <p className="text-sm text-neutral-500">
          No drafts yet. Generate one from a supplier match on a solicitation page.
        </p>
      )}

      {drafts.map((draft) => {
        const e = editing[draft.id];
        const statusColor =
          draft.status === "replied"
            ? "text-emerald-400"
            : draft.status === "sent"
            ? "text-blue-400"
            : "text-neutral-400";
        return (
          <div key={draft.id} className="border border-neutral-800 rounded p-4 flex flex-col gap-2">
            <div className="flex justify-between items-center">
              <span className={`text-xs uppercase ${statusColor}`}>Status: {draft.status}</span>
              {draft.sent_at && (
                <span className="text-xs text-neutral-500">
                  sent {new Date(draft.sent_at).toLocaleString()}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-neutral-500 w-12">To</span>
              <input
                className="flex-1 bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-sm"
                value={e?.to ?? ""}
                onChange={(ev) => patch(draft.id, "to", ev.target.value)}
                placeholder="supplier@example.com"
                type="email"
              />
            </div>

            <input
              className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1"
              value={e?.subject ?? ""}
              onChange={(ev) => patch(draft.id, "subject", ev.target.value)}
            />
            <textarea
              className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 h-40 font-mono text-sm"
              value={e?.body ?? ""}
              onChange={(ev) => patch(draft.id, "body", ev.target.value)}
            />

            <div className="flex gap-2">
              <button
                onClick={() => save(draft.id)}
                className="text-sm bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5 rounded"
              >
                Save edits
              </button>
              <button
                onClick={() => send(draft.id)}
                disabled={busy === draft.id}
                className="text-sm bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-white px-3 py-1.5 rounded"
              >
                {busy === draft.id ? "Sending…" : draft.status === "draft" ? "Send" : "Send again"}
              </button>
            </div>

            {draft.replies.length > 0 && (
              <div className="mt-2 flex flex-col gap-2 border-t border-neutral-800 pt-3">
                <p className="text-xs uppercase text-neutral-500">
                  Replies ({draft.replies.length})
                </p>
                {draft.replies.map((r) => (
                  <div key={r.id} className="bg-neutral-900/60 border border-neutral-800 rounded p-3">
                    <div className="flex items-center gap-3 flex-wrap text-xs text-neutral-400">
                      <span className="text-neutral-300">{r.from_addr}</span>
                      {r.received_at && <span>{new Date(r.received_at).toLocaleString()}</span>}
                      {r.extracted_price != null && (
                        <span className="bg-emerald-950 text-emerald-300 px-2 py-0.5 rounded font-mono">
                          quote ${r.extracted_price.toLocaleString()}
                        </span>
                      )}
                      {r.extracted_lead_time && (
                        <span className="bg-neutral-800 text-neutral-300 px-2 py-0.5 rounded">
                          {r.extracted_lead_time}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-neutral-300 mt-2 whitespace-pre-wrap line-clamp-6">
                      {r.body}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
