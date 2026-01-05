from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.routes_healing import router as healing_router
from app.api.routes_ci import router as ci_router
from app.api.routes_reports import router as reports_router
from app.db.session import init_db

app = FastAPI(
    title="PTQA Service",
    description="Predictive Testing & Quality Assessment Microservice",
    version="1.0.0",
)

# Optional but safe: allow CORS (handy if you later open UI from other origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in real prod you would restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {"message": "PTQA service is running"}


# --- SIMPLE UI ROUTE ---
@app.get("/ui", response_class=HTMLResponse)
def ptqa_ui():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>PTQA Console</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 20px;
      background: #f5f5f5;
    }
    h1 {
      margin-bottom: 0.2rem;
    }
    h2 {
      margin-top: 2rem;
      margin-bottom: 0.5rem;
    }
    .container {
      max-width: 1100px;
      margin: 0 auto;
      background: #ffffff;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    textarea, input[type="text"] {
      width: 100%;
      box-sizing: border-box;
      font-family: Consolas, monospace;
      font-size: 13px;
      padding: 8px;
      margin-bottom: 10px;
    }
    textarea {
      min-height: 420px;
      resize: vertical;
    }
    button {
      padding: 8px 14px;
      margin-right: 10px;
      border-radius: 4px;
      border: none;
      cursor: pointer;
      font-size: 14px;
    }
    button.primary {
      background-color: #2563eb;
      color: #fff;
    }
    button.secondary {
      background-color: #64748b;
      color: #fff;
    }
    .row {
      margin-bottom: 1rem;
    }
    label {
      font-weight: 600;
      display: block;
      margin-bottom: 4px;
    }
    .small {
      font-size: 12px;
      color: #555;
    }
    .two-col {
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 20px;
    }
    .badge {
      display: inline-block;
      padding: 2px 6px;
      font-size: 11px;
      border-radius: 3px;
      background: #e0f2fe;
      color: #0369a1;
      margin-left: 6px;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>PTQA Interactive Console</h1>
    <p class="small">
      Use this page to send healing events to <code>/ptqa/evaluate-healing</code> and view
      decisions or reports stored in SQLite.
    </p>

    <div class="two-col">
      <!-- LEFT: Input -->
      <div>
        <h2>1. Healing Event Payload</h2>
        <div class="row">
          <label for="payload">Payload JSON</label>
          <textarea id="payload">
{
  "metadata": {
    "healing_id": "H1001",
    "script_id": "BOT_LOGIN",
    "environment": "prod",
    "last_n_failures": 3
  },
  "healing_summary": {
    "status": "success",
    "old_locator": "//*[@id='username-old']",
    "new_locator": "//*[@id='username']",
    "strategy_used": "visual-ocr"
  },
  "model_info": {
    "model_confidence": 0.62
  },
  "script_output": {
    "original_script_path": "bots/login_bot.py",
    "healed_script_path": "bots/login_bot_healed.py"
  }
}
          </textarea>
          <button class="primary" onclick="evaluateHealing()">Evaluate Healing</button>
        </div>

        <h2>2. Report Lookup</h2>
        <div class="row">
          <label for="healingId">
            Healing ID
            <span class="badge">used for /ptqa/report/{healing_id}</span>
          </label>
          <input id="healingId" type="text" value="H1001" />
          <button class="secondary" onclick="getReport()">Get Report</button>
        </div>
      </div>

      <!-- RIGHT: Output -->
      <div>
        <h2>Response</h2>
        <p class="small">The JSON response from the PTQA service will appear here.</p>
        <textarea id="result" readonly></textarea>
      </div>
    </div>
  </div>

  <script>
    async function evaluateHealing() {
      const payloadText = document.getElementById("payload").value;
      let payload;
      try {
        payload = JSON.parse(payloadText);
      } catch (e) {
        alert("Payload is not valid JSON: " + e.message);
        return;
      }

      try {
        const res = await fetch("/ptqa/evaluate-healing", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        const data = await res.json();
        document.getElementById("result").value = JSON.stringify(data, null, 2);

        // If healing_id present in payload, sync it into the Healing ID input
        if (payload.metadata && payload.metadata.healing_id) {
          document.getElementById("healingId").value = payload.metadata.healing_id;
        }
      } catch (err) {
        document.getElementById("result").value = "Error calling /ptqa/evaluate-healing: " + err;
      }
    }

    async function getReport() {
      const healingId = document.getElementById("healingId").value.trim();
      if (!healingId) {
        alert("Please enter a healing_id first.");
        return;
      }

      try {
        const res = await fetch(`/ptqa/report/${encodeURIComponent(healingId)}`);
        const text = await res.text();

        // Try to parse JSON, but also show raw text in case of HTML error
        try {
          const data = JSON.parse(text);
          document.getElementById("result").value = JSON.stringify(data, null, 2);
        } catch {
          document.getElementById("result").value = text;
        }
      } catch (err) {
        document.getElementById("result").value = "Error calling /ptqa/report: " + err;
      }
    }
  </script>
</body>
</html>
    """


# Register PTQA routers
app.include_router(healing_router, prefix="/ptqa", tags=["Healing Evaluation"])
app.include_router(ci_router, prefix="/ptqa", tags=["CI/CD Quality Gate"])
app.include_router(reports_router, prefix="/ptqa", tags=["Reports"])
