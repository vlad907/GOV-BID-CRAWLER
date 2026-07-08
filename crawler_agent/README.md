# Crawler Agent

Runs on the machine that does the actual browsing. Exposes a small HTTP API
(`POST /jobs`, `GET /jobs/{id}`) that the main backend polls. Uses a real,
non-headless Chrome window (via Selenium) + BeautifulSoup for parsing, on the
theory that a visible, human-driven-looking browser is less likely to trip
bot detection than headless Chrome.

## Setup (Ubuntu)

Recommended OS for the dedicated crawler machine — see the top-level
`README.md` for why (real Chrome inside a virtual display, no GUI-session
dependency, survives reboots via systemd).

```bash
# Chrome
sudo apt update
sudo apt install -y wget gnupg xvfb x11vnc python3-venv python3-pip
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update && sudo apt install -y google-chrome-stable

# app
cd crawler_agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Selenium Manager (bundled since Selenium 4.25+) auto-resolves a matching
`chromedriver` for whatever Chrome version is installed — no manual driver
download needed.

## Running by hand (for the first selector-tuning pass)

Xvfb has no physical monitor, so to actually *watch* Chrome while you tune
the selectors in `app/selectors.py`, run `x11vnc` alongside it and connect
with any VNC viewer from your main machine:

```bash
Xvfb :99 -screen 0 1920x1080x24 &
x11vnc -display :99 -forever -nopw &
DISPLAY=:99 uvicorn app.main:app --host 0.0.0.0 --port 8100
```

Then VNC to `<crawler-machine-ip>:5900` while you submit test jobs (see
below) — you'll see the real Chrome window and can compare it against the
selectors live.

## Running for real (systemd, no monitor needed after tuning)

Once selectors are confirmed, drop the VNC step and let `xvfb-run` own the
virtual display for the life of the service:

`/etc/systemd/system/crawler-agent.service`:

```ini
[Unit]
Description=Gov Bid Crawler Agent
After=network.target

[Service]
Type=simple
User=crawler
WorkingDirectory=/opt/gov-bid-scheme/crawler_agent
ExecStart=/usr/bin/xvfb-run -a --server-args="-screen 0 1920x1080x24" \
  /opt/gov-bid-scheme/crawler_agent/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8100
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now crawler-agent
sudo ufw allow from <backend-machine-ip> to any port 8100 proto tcp   # if ufw is on
```

The backend's `.env` `CRAWLER_AGENT_URL` should point at
`http://<this-machine-ip>:8100`.

## Important: selectors will need tuning

The CSS selectors in `app/jobs/dibbs_search.py`, `app/jobs/sam_search.py`, and
`app/jobs/nsn_marketplace.py` are best-effort placeholders — DIBBS sits
behind a DoD warning/consent interstitial that has to be clicked through
before the real search form is reachable, and sam.gov/search is a
client-rendered SPA. Neither site's live DOM was inspected while building
this (no automated tooling should be poking a .mil-adjacent system
repeatedly, and sam.gov's SPA structure can't be read from static HTML
fetches). All selectors are centralized in `app/selectors.py` — the very
first thing to do on a real run is:

1. Start the agent using the "Running by hand" steps above (so you can
   actually see the browser via VNC), then submit one test job with curl:
   ```
   curl -X POST http://localhost:8100/jobs \
     -H "Content-Type: application/json" \
     -d '{"type": "sam_search", "params": {"keyword": "bracket"}}'
   ```
2. Watch the real Chrome window over VNC, and compare what it lands on to
   `app/selectors.py`.
3. Adjust selectors there until the parsed result (`GET /jobs/{job_id}`)
   matches what's on screen.

## Job types

- `dibbs_search` — `{"nsn": "...", "keyword": "..."}` → list of open RFQs
- `sam_search` — `{"keyword": "...", "naics_code": "...", "classification_code": "...", "set_aside_type": "..."}` → list of open solicitations
- `nsn_marketplace` — `{"nsn": "..."}` → list of candidate suppliers/listings

## Troubleshooting: "session not created: Chrome instance exited"

If you ever see this error, it almost always means Chrome tried to open
against a profile directory it thinks is already locked - either a genuinely
open instance, or stale `SingletonLock`/`SingletonCookie`/`SingletonSocket`
files left behind by a killed process. `app/browser.py` clears those files
before every launch and `CHROME_PROFILE_DIR` defaults to an absolute path
specifically to avoid this (a relative path can resolve against an
unexpected working directory once Chrome is launched through
chromedriver/subprocess indirection, silently falling back to your **real**
default Chrome profile and colliding with your actual browser). If it still
happens: check for orphaned Chrome/chromedriver processes (`ps aux | grep
chrome_profile`) and kill them, and confirm `CHROME_PROFILE_DIR` (if you've
overridden it in `.env`) is an absolute path.
