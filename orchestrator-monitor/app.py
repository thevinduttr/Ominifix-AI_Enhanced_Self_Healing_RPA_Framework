from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from heartbeat_handler import process_heartbeat, bots
from failure_detector import start_failure_detection

app = FastAPI()

# Serve static UI files from the `static` folder
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/heartbeat")
async def heartbeat(data: dict):
    return process_heartbeat(data)


@app.get("/status")
async def status():
    # Return current bots dictionary
    return JSONResponse({"bots": bots})


start_failure_detection()  # Start background monitoring
