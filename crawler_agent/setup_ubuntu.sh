#!/usr/bin/env bash
# One-shot setup + run for the crawler agent on a fresh Ubuntu box.
# Safe to re-run - every step checks whether it's already done first.
#
# Usage: ./setup_ubuntu.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v apt >/dev/null 2>&1; then
  echo "This script is for Ubuntu/Debian (needs apt). Exiting." >&2
  exit 1
fi

echo "==> Installing system packages (xvfb, x11vnc, python3-venv, chrome deps)..."
sudo apt update
sudo apt install -y wget gnupg xvfb x11vnc python3-venv python3-pip unzip

if ! command -v google-chrome >/dev/null 2>&1; then
  echo "==> Installing Google Chrome..."
  wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
  echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
  sudo apt update
  sudo apt install -y google-chrome-stable
else
  echo "==> Google Chrome already installed, skipping."
fi

if [ ! -d venv ]; then
  echo "==> Creating Python venv..."
  python3 -m venv venv
fi

echo "==> Installing Python dependencies..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "==> Starting virtual display (Xvfb :99) if not already running..."
if ! pgrep -f "Xvfb :99" >/dev/null 2>&1; then
  Xvfb :99 -screen 0 1920x1080x24 &
  sleep 1
fi

echo "==> Starting x11vnc on :99 (port 5900) if not already running..."
if ! pgrep -f "x11vnc -display :99" >/dev/null 2>&1; then
  x11vnc -display :99 -forever -nopw >/tmp/x11vnc.log 2>&1 &
  sleep 1
fi

MACHINE_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "==> Setup done."
echo "    VNC into this machine to watch the browser: vnc://${MACHINE_IP}:5900"
echo "    (on a Mac: Finder -> Go -> Connect to Server -> vnc://${MACHINE_IP}:5900)"
echo ""
echo "==> Starting the crawler agent on port 8100 (Ctrl+C to stop)..."
DISPLAY=:99 uvicorn app.main:app --host 0.0.0.0 --port 8100
