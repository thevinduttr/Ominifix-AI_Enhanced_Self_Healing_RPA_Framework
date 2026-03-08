#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:99

# Clean stale display lock/socket left by prior failed runs.
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99

Xvfb :99 -screen 0 1920x1080x24 -ac +extension RANDR > /tmp/xvfb.log 2>&1 &
XVFB_PID=$!

# Wait briefly for Xvfb and validate it is alive.
sleep 1
if ! kill -0 "$XVFB_PID" 2>/dev/null; then
	echo "[vnc] Xvfb failed to start. See /tmp/xvfb.log"
	cat /tmp/xvfb.log || true
	echo "[vnc] Falling back to HEADLESS=true to keep bot running."
	unset DISPLAY
	export HEADLESS=true
	exec python rpa/run_healed_or_original.py
fi

fluxbox > /tmp/fluxbox.log 2>&1 &
x11vnc -display :99 -forever -shared -nopw -listen 0.0.0.0 -rfbport 5900 > /tmp/x11vnc.log 2>&1 &
websockify --web=/usr/share/novnc/ 6080 localhost:5900 > /tmp/websockify.log 2>&1 &

# Give display services a moment to initialize before starting Playwright.
sleep 2

exec python rpa/run_healed_or_original.py
