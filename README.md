# Gov Bid Sourcing

Locally-hosted tool for finding government part solicitations (SAM.gov,
DIBBS), filtering for set-asides (SDVOSB/small business), matching NSNs to
candidate suppliers, and drafting manufacturer outreach + bid pricing.
Outreach sending and bid submission are always human-reviewed — nothing goes
out automatically.

Three services:

- **`backend/`** — FastAPI + SQLite. Single source of truth. Orchestrates
  crawl jobs on the crawler agent for both SAM.gov and DIBBS search, plus NSN
  marketplace supplier lookups.
- **`frontend/`** — Next.js UI: solicitations list/filters, supplier matches,
  outreach drafts, bid drafts.
- **`crawler_agent/`** — runs on a second machine, drives a real (non-headless)
  Chrome via Selenium + BeautifulSoup. Talks to the backend over plain LAN
  HTTP; the backend polls it for job status.

No accounts or API keys are required anywhere. SAM.gov and DIBBS opportunity
search are both public — the crawler agent just drives a real browser through
the public search pages (clicking past DIBBS's DoD consent banner where
needed) rather than calling an authenticated API.

## Running with Docker (recommended — one command)

Runs the backend and frontend together, no juggling terminals:

```bash
cp .env.example .env      # set CRAWL_AGENT_IP to your crawl machine's LAN IP
docker compose up         # add --build the first time or after dep changes
```

- Frontend: http://localhost:3000
- Backend:  http://localhost:8000
- Source is bind-mounted, so edits hot-reload without a rebuild.
- The SQLite DB stays at `backend/govbid.db` on the host, so pulled
  solicitations persist across restarts.

The crawler agent still runs separately on the Ubuntu box (see
`crawler_agent/README.md`); the containers reach it via `crawl.local:8100`,
pinned to `CRAWL_AGENT_IP` since containers can't resolve mDNS `.local`
names. If hot reload ever feels stale on macOS, add
`WATCHPACK_POLLING=true` under the frontend `environment:` in
`docker-compose.yml`.

## Running locally (without Docker)

```bash
# backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# frontend (separate terminal)
cd frontend
npm install
npm run dev

# crawler agent (on the crawler machine, separate terminal)
# recommended: dedicated Ubuntu box + Xvfb, see crawler_agent/README.md for
# full setup (Chrome install, systemd service, VNC for the first tuning pass)
cd crawler_agent
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8100
```

Then point `backend/.env`'s `CRAWLER_AGENT_URL` at the crawler machine's IP,
e.g. `http://192.168.1.50:8100`.

## Email setup (Gmail app password)

Optional — only needed to send outreach and pull replies. Uses standard
SMTP/IMAP with a Gmail **app password**, so there's no Google Cloud project
or OAuth to deal with.

1. On the Gmail account, turn on **2-Step Verification**
   (myaccount.google.com → Security). Google won't issue an app password
   without it.
2. Go to myaccount.google.com/apppasswords, name it "Gov Bid", and copy the
   16-character password it gives you (spaces don't matter).
3. In `backend/.env` set:
   ```
   SMTP_USER=youraddress@gmail.com
   SMTP_PASSWORD=that-16-char-app-password
   EMAIL_FROM_NAME=Your Company
   ```
   (`SMTP_HOST`/`IMAP_HOST` already default to Gmail's servers.)
4. Restart the backend.

Then on the **Outreach** page: fill each draft's **To** field, click **Send**
(nothing sends without that click), and use **Sync replies** to pull supplier
responses — a quoted price and lead time are auto-extracted and shown on the
reply. IMAP access is read-only; the app never deletes or moves your mail.

## Status / known gaps

- The crawler agent's job queue, HTTP API, and Selenium driver management are
  built and were verified to launch a real Chrome window successfully when
  run directly on this machine. **The SAM.gov, DIBBS, and NSN-marketplace CSS
  selectors in `crawler_agent/app/selectors.py` are best-effort placeholders**
  — DIBBS sits behind a DoD consent interstitial and sam.gov/search is a
  client-rendered SPA, and neither site's live DOM was inspected while
  building this. Run one real job per source and adjust selectors against
  what actually loads — see `crawler_agent/README.md`.
- Bid draft markup logic (`backend/app/services/markup.py`) is a starting
  suggestion (default markup, capped against a manually-entered benchmark
  award price) for a human to review, not an authoritative pricing engine.
  There's no automated "pull last award price" yet — that field is entered
  by hand on the solicitation page for now.
- The SBA Non-Manufacturer Rule badge is a lightweight heuristic (set-aside
  type + estimated value vs. threshold), not a compliance engine — always
  verify manually before bidding as a reseller on a set-aside.
