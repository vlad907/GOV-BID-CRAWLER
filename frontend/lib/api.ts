const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${init?.method ?? "GET"} ${path} failed (${res.status}): ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface Solicitation {
  id: number;
  source: string;
  solicitation_id: string;
  nsn?: string | null;
  title?: string | null;
  description?: string | null;
  qty?: number | null;
  naics_code?: string | null;
  set_aside_type?: string | null;
  is_sdvosb: boolean;
  close_date?: string | null;
  specs?: Record<string, unknown> | null;
  raw_url?: string | null;
  status: string;
  created_at: string;
  nmr_may_apply: boolean;
}

export interface Supplier {
  id: number;
  name: string;
  cage_code?: string | null;
  source_marketplace?: string | null;
  contact_email?: string | null;
  url?: string | null;
  notes?: string | null;
}

export interface SupplierMatch {
  id: number;
  solicitation_id: number;
  supplier_id: number;
  matched_nsn?: string | null;
  source_page_url?: string | null;
  scraped_price?: number | null;
  created_at: string;
  supplier: Supplier;
}

export interface OutreachDraft {
  id: number;
  supplier_match_id: number;
  draft_subject: string;
  draft_body: string;
  status: string;
  sent_at?: string | null;
  created_at: string;
}

export interface BidDraft {
  id: number;
  solicitation_id: number;
  cost_basis?: number | null;
  suggested_markup_pct?: number | null;
  suggested_price?: number | null;
  benchmark_award_price?: number | null;
  status: string;
  submitted_at?: string | null;
  created_at: string;
}

export interface SolicitationFilters {
  source?: string;
  set_aside_type?: string;
  is_sdvosb?: boolean;
  nsn?: string;
  q?: string;
}

export const api = {
  listSolicitations: (filters: SolicitationFilters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== "") params.set(key, String(value));
    });
    const qs = params.toString();
    return request<Solicitation[]>(`/api/solicitations${qs ? `?${qs}` : ""}`);
  },
  getSolicitation: (id: number) => request<Solicitation>(`/api/solicitations/${id}`),
  getSolicitationMatches: (id: number) =>
    request<SupplierMatch[]>(`/api/solicitations/${id}/matches`),
  getSolicitationBidDrafts: (id: number) =>
    request<BidDraft[]>(`/api/solicitations/${id}/bid-drafts`),

  createCrawlJob: (payload: { type: string; params?: Record<string, unknown>; solicitation_id?: number }) =>
    request<{ job_id: string; status: string }>("/api/crawl-jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getCrawlJob: (jobId: string) => request<{ status: string; result?: unknown; error?: string }>(
    `/api/crawl-jobs/${jobId}`
  ),

  generateOutreach: (supplierMatchId: number) =>
    request<OutreachDraft>(`/api/outreach/generate/${supplierMatchId}`, { method: "POST" }),
  listOutreachDrafts: (status?: string) =>
    request<OutreachDraft[]>(`/api/outreach${status ? `?status=${status}` : ""}`),
  updateOutreachDraft: (id: number, payload: Partial<OutreachDraft>) =>
    request<OutreachDraft>(`/api/outreach/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),

  listBidDrafts: (status?: string) =>
    request<BidDraft[]>(`/api/bid-drafts${status ? `?status=${status}` : ""}`),
  createBidDraft: (payload: { solicitation_id: number; benchmark_award_price?: number; markup_pct?: number; cost_basis?: number }) =>
    request<BidDraft>("/api/bid-drafts", { method: "POST", body: JSON.stringify(payload) }),
  updateBidDraft: (id: number, payload: Partial<BidDraft>) =>
    request<BidDraft>(`/api/bid-drafts/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
};
