#!/bin/bash
cd "$(dirname "$0")"
exec /opt/homebrew/bin/python3.10 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
