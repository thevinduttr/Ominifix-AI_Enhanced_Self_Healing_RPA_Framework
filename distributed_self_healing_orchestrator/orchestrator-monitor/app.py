from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from heartbeat_handler import process_heartbeat, process_failure, bots, failures
from failure_detector import start_failure_detection
from pathlib import Path
import os

# Get the directory of this file
SCRIPT_DIR = Path(__file__).parent

app = FastAPI()

# Serve static UI files from the `static` folder
static_dir = SCRIPT_DIR / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Log effective model URL on startup for quick diagnostics
print(f"[startup] MODEL_URL={os.environ.get('MODEL_URL') or '<unset>'}")


@app.get("/")
async def index():
    return FileResponse(str(SCRIPT_DIR / "static" / "index.html"))


@app.post("/heartbeat")
async def heartbeat(data: dict):
    return process_heartbeat(data)


@app.post('/report_failure')
async def report_failure(data: dict):
    print(f"🔍 RECEIVED FAILURE DATA KEYS: {list(data.keys())}")
    print(f"🔍 RECEIVED DATA: {data}")
    result = process_failure(data)
    print(f"🔍 PROCESS RESULT: {result}")
    return result


@app.get("/status")
async def status():
    # Return current bots dictionary
    # Return bots and recent failures
    return JSONResponse({"bots": bots, "failures": failures})


start_failure_detection()  # Start background monitoring
