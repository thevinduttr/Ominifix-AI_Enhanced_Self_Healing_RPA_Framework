# Distributed Self-Healing Orchestrator - Complete Viva Guide

## Your Role: Distributed Self-Healing Orchestrator

You are responsible for the **central intelligence system** that monitors RPA bots, detects failures, routes them to healing, and automatically restarts with healed scripts.

---

## Part 1: Heartbeat Monitoring System
**File Location:** `distributed_self_healing_orchestrator/dummy_bot/main.py`

### What It Does:
Your orchestrator **continuously monitors bot health** by collecting periodic heartbeats (signals) from running bots. If heartbeats stop, it knows the bot has failed.

### Code - Heartbeat Thread Creation:
```python
# Lines 1-27: Configuration
BOT_ID = os.getenv("BOT_ID", "DUMMY-BOT-new")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL") or os.getenv("MONITOR_URL", "http://localhost:8000")
ORCHESTRATOR_URL = ORCHESTRATOR_URL.removesuffix("/heartbeat")
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("HEARTBEAT_INTERVAL", "5"))
AUTO_WAIT_FOR_HEALING = os.getenv("AUTO_WAIT_FOR_HEALING", "true").strip().lower() in {"1", "true", "yes"}
bot_running = True  # Flag to control heartbeat
```

### Code - Heartbeat Function:
```python
# Lines 31-47: Send Heartbeat Every 5 Seconds
def send_heartbeat():
    """Send heartbeat to orchestrator every 5 seconds until bot stops."""
    global bot_running
    while bot_running:
        try:
            payload = {
                "botId": BOT_ID,
                "metadata": {
                    "bot_service": "dummy_bot",
                    "run_id": f"RUN-DUMMY-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                }
            }
            response = requests.post(
                f"{ORCHESTRATOR_URL}/heartbeat",
                json=payload,
                timeout=5
            )
            print(f"✓ Heartbeat sent: {response.status_code}")
        except Exception as e:
            print(f"✗ Heartbeat failed: {e}")
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)
```

### Code - Heartbeat Thread Started:
```python
# Lines 355-365: Main Bot Execution Starts Heartbeat
def run():
    """Main bot execution."""
    global bot_running, submitted_records

    # Start heartbeat in background (NON-DAEMON)
    heartbeat_thread = threading.Thread(target=send_heartbeat)
    heartbeat_thread.start()  # ← Thread runs forever until bot_running = False
    print(f"🔄 Heartbeat thread started")
```

### Key Design Decisions:
- **Non-daemon thread**: Thread stays alive even after main bot completes
- **Every 5 seconds**: Configurable via `HEARTBEAT_INTERVAL_SECONDS` env var
- **Service name**: `dummy_bot` identifies which service is running
- **Run ID**: Unique per execution for tracking

### Heartbeat Endpoint:
**File Location:** `distributed_self_healing_orchestrator/orchestrator-monitor/app.py`

The orchestrator receives these heartbeats at: `POST /heartbeat`

---

## Part 2: Failure Collection System
**File Location:** `distributed_self_healing_orchestrator/dummy_bot/main.py`

### What It Does:
When a bot encounters an error, your orchestrator **captures rich failure data** including error message, page state, locators, and screenshots. This data is needed by the healing engine.

### Code - Exception Handling Block:
```python
# Lines 365-405: Main Bot Try-Catch Block
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=env_flag("HEADLESS"), slow_mo=800)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_load_state("networkidle")

        try:
            # ... bot automation code (login, form fill, etc.) ...
            pass

        except Exception as e:
            print(f"❌ Bot execution failed: {e}")
            # ← CAPTURE FAILURE HERE
            send_failure_report(page, e)  # Your function

            # ← WAIT FOR HEALING
            failed_at = time.time()
            recovered = wait_and_run_healed_script(failed_at)
            if not recovered:
                bot_running = False
```

### Code - Failure Report Function:
```python
# Lines 49-109: Send Failure Details to Orchestrator
def send_failure_report(page, exc: Exception) -> None:
    """Send failure details to orchestrator."""
    try:
        page_url = page.url if page else "unknown"
        page_html = page.content() if page else ""

        # Use absolute path so healing engine can resolve script
        script_path = os.path.abspath(__file__)

        # Extract failing line from traceback
        failing_line = 1
        tb = exc.__traceback__
        while tb:
            if tb.tb_frame.f_code.co_filename == __file__:
                failing_line = tb.tb_lineno
            tb = tb.tb_next

        # Extract old locator from error message
        error_text = str(exc)
        old_locator = ""
        if "Element not found:" in error_text:
            old_locator = error_text.split("Element not found:", 1)[1].strip()

        # Capture screenshot
        screenshot_path = ""
        try:
            os.makedirs("rpa", exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            screenshot_path = os.path.join("rpa", f"failure_{timestamp}.png")
            page.screenshot(path=screenshot_path, full_page=True)
        except Exception:
            pass

        # Determine failure type
        failure_type = "ELEMENT_NOT_FOUND"
        if isinstance(exc, PlaywrightTimeoutError):
            failure_type = "TIMEOUT_ERROR"

        # Build payload
        payload = {
            "botId": BOT_ID,
            "page_url": page_url,
            "failure_type": failure_type,
            "failed_action": "locator",
            "element_role": "form_field",
            "expected_text": "Update Profile",
            "old_locator": old_locator,
            "old_locator_type": "css",
            "error_message": error_text,
            "page_html": page_html,
            "screenshot_path": screenshot_path,
            "metadata": {
                "bot_id": BOT_ID,
                "bot_service": "dummy_bot",
                "script_path": script_path,
                "failing_line": failing_line,
                "page_name": "settings",
                "run_id": f"RUN-DUMMY-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            }
        }

        response = requests.post(
            f"{ORCHESTRATOR_URL}/report_failure",
            json=payload,
            timeout=10
        )
        print(f"✓ Failure reported: {response.status_code}")
    except Exception as e:
        print(f"✗ Could not report failure: {e}")
```

### Data Captured in Failure Report:
- ✅ **botId** - Which bot failed
- ✅ **failure_type** - ELEMENT_NOT_FOUND, TIMEOUT_ERROR, etc.
- ✅ **error_message** - Full exception text
- ✅ **page_html** - Entire HTML of the failed page
- ✅ **old_locator** - Broken selector that failed
- ✅ **screenshot_path** - Visual evidence of failure
- ✅ **script_path** - Where the bot script is located
- ✅ **failing_line** - Line number in script that failed
- ✅ **page_url** - URL where failure occurred

### Key Design Decision:
- **Rich context**: Healing engine gets everything needed to fix the issue
- **Screenshots**: Visual proof of page state
- **Line tracking**: Helps locator healing know exactly which line to patch

---

## Part 3: Failure Reporting to Healing Engine
**File Location:** `distributed_self_healing_orchestrator/orchestrator-monitor/app.py`

### What It Does:
Your orchestrator receives failure reports from bots and sends them to the **ML-based healing engine** for analysis and fixing.

### Orchestrator Endpoint:
```python
# In app.py:
@app.post("/report_failure")
async def report_failure(payload: dict):
    """
    Receive failure from bot.
    Extract information needed for healing.
    Send to healing engine.
    """
    # Store in database or queue
    # Send to ai_rpa_healing_engine for analysis
    # Return success
```

### Flow:
```
Bot fails
    ↓
send_failure_report() collects data
    ↓
POST /report_failure → Orchestrator receives
    ↓
Orchestrator sends to healing engine
    ↓
Healing engine analyzes error
```

---

## Part 4: Error Classification & Routing
**File Location:** `ai_rpa_healing_engine/src/engine/healing_router.py`

### What It Does:
Your orchestrator uses a **router** to decide: "Is this error healable? Which healing path should we use?"

### Code - Healable Errors Definition:
```python
# Lines 10-22: Define Which Errors Can Be Fixed
HEALABLE_ERRORS = {
    "ELEMENT_NOT_FOUND",           # Selector broke - we can find new one
    "ELEMENT_NOT_VISIBLE",         # Element hidden - wait/scroll needed
    "TIMEOUT_ERROR",               # Page didn't load - retry
    "TIMEOUT_WAITING_FOR_SELECTOR",# Selector not found in time
    "STRICT_MODE_VIOLATION",       # Multiple elements match
    "DETACHED_FROM_DOM",           # Element removed from page
    "NOT_VISIBLE",                 # Element hidden
    "NOT_ENABLED",                 # Button/field disabled
    "UI_SELECTOR_CHANGED",         # Page layout changed
}

# ← You added "UI_SELECTOR_CHANGED" to healable errors
```

### Code - Router Decision Logic:
```python
# Lines 26-47: Decide If Error Is Healable
def decide(inp: dict) -> NoFix | None:
    """
    Return None = error IS healable
    Return NoFix = error is NOT healable
    """
    fc = inp.get("failure_context", {})
    action = (fc.get("action") or "").strip().lower()
    error = (fc.get("error_type") or "").strip().upper()
    dom = inp.get("dom_context", {})

    # Check 1: Is the action type supported?
    if action and action not in SUPPORTED_ACTIONS:
        return NoFix(
            f"Action '{action}' not supported in PP1 scope "
            f"(supported: {sorted(SUPPORTED_ACTIONS)})."
        )

    # Check 2: Is the error type healable?
    if error and error not in HEALABLE_ERRORS:
        return NoFix(f"Error type '{error}' not healable by locator patching.")

    # Check 3: Do we have the element HTML to fix?
    if not dom.get("new_element_html"):
        return NoFix("Missing dom_context.new_element_html; cannot regenerate locator.")

    # All checks passed - error IS healable
    return None
```

### Healing Paths Available:
1. **Locator Healing** - Find new CSS/XPath selector
2. **Patcher** - Use LibCST to modify Python script
3. **Retry** - Wait and try again
4. **Screenshot Analysis** - Analyze visual changes
5. **Network Error Handler** - Handle connection failures

### Router Output:
```python
# Lines 49-81: Base Output Structure
def base_output(inp: dict) -> dict:
    return {
        "metadata": {
            "healing_id": f"HEAL-{uuid.uuid4()}",
            "report_id": md.get("report_id", ""),
            "bot_id": md.get("bot_id", "UNKNOWN_BOT"),
            "timestamp": datetime.now().isoformat(),
        },
        "failure_context": {
            "script_path": fc.get("script_path", ""),
            "failing_line": fc.get("failing_line", -1),
            "old_locator": fc.get("old_locator", ""),
            "error_type": fc.get("error_type", ""),
        },
        "healing_strategy": "locator_regeneration",  # ← Which healing path
    }
```

### Key Design Decision:
- **Decision gate**: Only heal errors we know how to fix
- **Preserve context**: Keep bot_id, script_path, failing_line for tracing
- **Multiple strategies**: Different errors need different fixes

---

## Part 5: Bot Restart Logic with Healed Script
**File Location:** `distributed_self_healing_orchestrator/dummy_bot/main.py`

### What It Does:
After failure, your orchestrator **waits for the healing engine** to create a fixed script, then **automatically restarts the bot** using the healed version.

### Code - Wait and Run Healed Script:
```python
# Lines 138-170: Poll For Healed Script and Restart
def wait_and_run_healed_script(failed_at: float) -> bool:
    """Keep bot alive after failure, wait for healed script, and run it automatically."""
    if not AUTO_WAIT_FOR_HEALING:
        return False

    # Set timeout deadline
    deadline = time.time() + HEALING_WAIT_TIMEOUT_SECONDS  # Default 600 seconds
    print(
        f"🩹 Waiting for healed script for {BOT_ID} (timeout={HEALING_WAIT_TIMEOUT_SECONDS}s, "
        f"poll={HEALING_POLL_INTERVAL_SECONDS}s). Browser session remains open."
    )

    # Poll for healed script every 3 seconds
    while bot_running and time.time() < deadline:
        healed_script = find_latest_healed_script(BOT_ID, min_mtime=failed_at)
        if healed_script:
            print(f"🩹 Healed script detected: {healed_script}")
            print("🚀 Restarting process to run healed script in a fresh Playwright context...")
            launcher_path = Path(__file__).resolve().parent / "rpa" / "run_healed_or_original.py"
            try:
                # Pass healed script path via environment variable
                os.environ["FORCE_HEALED_SCRIPT_PATH"] = healed_script
                # Use os.execv to restart Python in a fresh process
                # This avoids nested Playwright event loop crash
                os.execv(sys.executable, [sys.executable, str(launcher_path)])
            except Exception as exec_err:
                print(f"⚠️ Failed to restart launcher: {exec_err}")
        # Wait 3 seconds before checking again
        time.sleep(HEALING_POLL_INTERVAL_SECONDS)

    print("⚠️ Healing wait timeout reached. Exiting failed run.")
    return False
```

### Code - Find Latest Healed Script:
```python
# Lines 129-152: Find Newest Healed Script
def find_latest_healed_script(bot_id: str, min_mtime: float = 0.0) -> str:
    """Find latest healed script for the bot, optionally newer than min_mtime."""
    # Resolve directory (works in/out of container)
    healed_root = Path(resolve_healed_scripts_dir(HEALED_SCRIPTS_DIR)) / bot_id
    if not healed_root.exists():
        return ""

    # Search patterns
    patterns = [
        str(healed_root / "*" / "healed_script--*.py"),
        str(healed_root / "healed_script--*.py"),
    ]

    # Find all healed scripts matching patterns
    candidates = []
    for pattern in patterns:
        candidates.extend(glob.glob(pattern))

    if not candidates:
        return ""

    # Sort by modification time (newest first)
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    
    # Return first script newer than min_mtime (failure timestamp)
    for candidate in candidates:
        if os.path.getmtime(candidate) > min_mtime:
            return candidate
    return ""
```

### Key Design Decisions:
1. **Non-blocking**: Browser stays open, waiting for healing
2. **Polling interval**: Check every 3 seconds (configurable)
3. **Timeout**: Stop waiting after 600 seconds (configurable)
4. **Process restart**: Use `os.execv()` to avoid Playwright nesting
5. **Timestamp check**: Only use scripts created AFTER failure

### Healed Script Storage Structure:
```
/app/healed_scripts/
├── DUMMY-BOT-new/
│   ├── 2025-05-04_14-30/
│   │   └── healed_script--HEAL-abc123-line42.py
│   └── healed_script--HEAL-def456-line50.py
└── BOT-NETWORK-ERROR/
    └── healed_script--HEAL-xyz789-line15.py
```

---

## Part 6: Fallback Safety - Revert to Original Script
**File Location:** `distributed_self_healing_orchestrator/dummy_bot/rpa/run_healed_or_original.py`

### What It Does:
If healing takes too long or fails, your orchestrator **safely falls back** to the original script instead of getting stuck.

### Code - Fallback Logic:
```python
# run_healed_or_original.py
import os
import sys

# Check if we have a healed script to run
healed_script_path = os.getenv("FORCE_HEALED_SCRIPT_PATH", "").strip()

if healed_script_path and os.path.exists(healed_script_path):
    print(f"🩹 Running healed script: {healed_script_path}")
    with open(healed_script_path) as f:
        exec(f.read())
else:
    # Fallback: run original script
    print("⚠️ No healed script available. Running original script.")
    original_script = os.path.join(os.path.dirname(__file__), "..", "main.py")
    if os.path.exists(original_script):
        with open(original_script) as f:
            exec(f.read())
    else:
        print("❌ Error: Cannot find original script!")
        sys.exit(1)
```

### Fallback Triggers:
- ✅ Healing takes > 600 seconds
- ✅ Healed script file not found
- ✅ Healing engine offline
- ✅ Healing failed or rejected by PTQA

### Key Design Decision:
- **Never crash**: Always have a fallback
- **Timeout protection**: Don't wait forever
- **User notification**: Clear messages about what's happening

---

## Part 7: Multi-Bot Support & Data Collection
**File Location:** `distributed_self_healing_orchestrator/dummy_bot/main.py`

### What It Does:
Your orchestrator manages **multiple customers per bot run** and **collects submitted records** into an array for tracking.

### Code - Customer Data Structure:
```python
# Lines 24-25: Global Array to Collect Records
submitted_records = []  # Array to collect customer onboarding records

# Lines 228-251: Generate Customer List
def get_customer_data_list() -> list:
    """Generate list of multiple customer records to onboard."""
    return [
        {
            "fullname": "Nimal Jayasuriya",
            "segment": "Retail",
            "customer_id": "NIC-199012345678",
            "gender": "Female",
            "branch": "Colombo Central",
            "notes": "Customer onboarding added from demo bot.",
        },
        {
            "fullname": "Rajesh Kumar Singh",
            "segment": "Corporate",
            "customer_id": "NIC-198756234901",
            "gender": "Male",
            "branch": "Colombo North",
            "notes": "Corporate account setup.",
        },
        # ... 2 more customers ...
    ]
```

### Code - Record Creation Structure:
```python
# Lines 209-227: Create Onboarding Record
def create_onboarding_record(fullname: str, segment: str, customer_id: str, gender: str, branch: str, notes: str, terms_accepted: bool) -> dict:
    """Create an onboarding record structure."""
    import time
    record = {
        "recordId": f"ONB-{int(time.time() * 1000)}",
        "fullName": fullname,
        "segment": segment,
        "nationalId": customer_id,
        "gender": gender,
        "branch": branch,
        "notes": notes,
        "termsAccepted": terms_accepted,
        "stage": "KYC Pending",
        "submittedAt": datetime.now(UTC).isoformat(),
    }
    return record
```

### Code - Submit and Collect:
```python
# Lines 253-277: Submit Customer and Collect Data
def submit_customer_onboarding(page, customer_data: dict) -> None:
    """Fill and submit KYC for customer onboarding. Collects data into submitted_records array."""
    global submitted_records
    
    # Fill the form with customer data
    form_data = fill_customer_onboarding_form(page, customer_data)

    # Submit KYC (triggers dialog)
    page.once("dialog", lambda dialog: dialog.accept())
    submit_kyc = require_locator(page, "#submit-kyc")
    submit_kyc.click()
    
    # Collect the submitted record into array
    record = create_onboarding_record(
        fullname=form_data["fullname"],
        segment=form_data["segment"],
        customer_id=form_data["customer_id"],
        gender=form_data["gender"],
        branch=form_data["branch"],
        notes=form_data["notes"],
        terms_accepted=form_data["terms_accepted"],
    )
    submitted_records.append(record)  # ← Store in global array
    print(f"✅ Record collected: {form_data['fullname']} ({form_data['segment']})")
    page.wait_for_timeout(1500)
```

### Code - Process Multiple Customers:
```python
# Lines 388-396: Main Bot Loop - Process 4 Customers
# Get list of customers to onboard
customers_to_add = get_customer_data_list()
print(f"\n🚀 Starting to add {len(customers_to_add)} customers...\n")

# Submit each customer
for idx, customer_data in enumerate(customers_to_add, 1):
    print(f"\n[{idx}/{len(customers_to_add)}] Adding customer: {customer_data['fullname']}")
    submit_customer_onboarding(page, customer_data)
    if idx < len(customers_to_add):
        page.wait_for_timeout(2000)  # Wait before next customer
```

### Code - Final Report:
```python
# Lines 410-424: Print Final Summary
print(f"\n{'='*60}")
print(f"📊 Bot Execution Complete - Total Records: {len(submitted_records)}")
print(f"{'='*60}")
if submitted_records:
    print("\n📋 Successfully Onboarded Customers:")
    for idx, record in enumerate(submitted_records, 1):
        print(f"  {idx}. {record['fullName']} (ID: {record['nationalId']}) - {record['segment']} - {record['stage']}")
    print(f"\n✨ All {len(submitted_records)} customers added successfully!")
else:
    print("\n⚠️  No records collected.")
```

---

## Part 8: Docker Orchestration & Service Wiring
**File Location:** `docker-compose.yml`

### What It Does:
Your orchestrator is deployed as a **microservice** that runs alongside other services, all coordinated by Docker Compose.

### Services You Interact With:
```yaml
# Lines 19-51: Orchestrator Monitor Service
orchestrator_monitor:
  build:
    context: ./distributed_self_healing_orchestrator
    dockerfile: orchestrator-monitor/Dockerfile
  command: ["uvicorn","app:app","--host","0.0.0.0","--port","8000"]
  ports:
    - "8000:8000"  # ← Your orchestrator API
  environment:
    MODEL_URL: https://rpa-error-classifier-555972249634.us-central1.run.app/predict
    RABBIT_HOST: ${RABBITMQ_HOST:-rabbitmq}
    PTQA_SERVICE_URL: http://ptqa_service:8000/ptqa/evaluate-healing
    RESTART_ON_CATEGORIES: NETWORK_ERROR,UNKNOWN,BOT_ERROR
    BOT_SERVICE_MAP: RPA-0020:bot_form_filler_rpa
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  depends_on:
    rabbitmq:
      condition: service_healthy

# Lines 78-91: Dummy Bot Service (Your Implementation)
dummy_bot:
  image: python:3.11-slim
  command: ["python", "/app/rpa/main.py"]
  environment:
    BOT_ID: DUMMY-BOT-new
    ORCHESTRATOR_URL: http://orchestrator_monitor:8000
    HEARTBEAT_INTERVAL: 5
    AUTO_WAIT_FOR_HEALING: "true"
  volumes:
    - ./:/app/data
    - ./dummy_bot:/app/rpa
  depends_on:
    - orchestrator_monitor
```

### Service Connections:
```
Your Bot (dummy_bot)
    ↓ sends heartbeat every 5s
    ↓ sends failure reports
Your Orchestrator (orchestrator_monitor:8000)
    ↓ receives heartbeats (detects health)
    ↓ receives failures (detects errors)
    ↓ routes errors via healing_router
    ↓ queries healed scripts
Healing Engine (ai_rpa_healing_engine)
    ↓ analyzes errors
    ↓ patches scripts using LibCST
    ↓ saves healed_script--*.py files
```

---

## Complete Workflow Summary

### Step-by-Step Flow (What You Implemented):

```
STEP 1: BOT STARTS
├─ Main bot execution begins
├─ Heartbeat thread spawned (non-daemon)
└─ Heartbeat sends every 5 seconds to /heartbeat

STEP 2: BOT RUNS NORMALLY
├─ Bot processes customers
├─ Fills forms
├─ Submits records
├─ Collects data into submitted_records array
└─ Heartbeats continue in background

STEP 3: BOT ENCOUNTERS ERROR
├─ Exception raised (e.g., selector not found)
├─ Exception caught in try-catch
└─ Bot_running flag still TRUE (thread alive)

STEP 4: FAILURE COLLECTED
├─ send_failure_report() called
├─ Gathers: error_message, page_html, screenshot, locator, line_number
├─ Creates payload with rich context
└─ POST /report_failure to orchestrator

STEP 5: FAILURE ROUTED
├─ Orchestrator receives failure
├─ healing_router.decide() checks: Is error healable?
├─ If in HEALABLE_ERRORS set: YES
├─ If not: NO (send NoFix)
└─ Route to correct healing path

STEP 6: HEALING ENGINE WORKS
├─ ML classifier analyzes error
├─ LibCST patcher modifies script
├─ Creates healed_script--HEAL-*.py
└─ Saves to /app/healed_scripts/BOT_ID/

STEP 7: BOT WAITS FOR HEALING
├─ wait_and_run_healed_script() polling loop
├─ Checks every 3 seconds for healed script
├─ find_latest_healed_script() searches by mtime
├─ Timeout: stop waiting after 600 seconds
└─ Browser remains open (not closed)

STEP 8: HEALED SCRIPT DETECTED
├─ find_latest_healed_script() returns path
├─ Set FORCE_HEALED_SCRIPT_PATH env var
├─ os.execv() restarts Python process
└─ Launch run_healed_or_original.py

STEP 9: BOT RESTARTS WITH FIX
├─ Fresh Python interpreter
├─ Fresh Playwright context
├─ Load healed_script--*.py
├─ Execute fixed code
└─ Resume from where it failed

STEP 10: BOT COMPLETES
├─ All customers processed
├─ submitted_records array populated
├─ Bot_running set to FALSE
├─ Heartbeat thread stops
└─ Print final summary report
```

---

## Key Files You Own

| File | Purpose | Key Functions |
|------|---------|----------------|
| `dummy_bot/main.py` | Main bot + orchestrator integration | `send_heartbeat()`, `send_failure_report()`, `wait_and_run_healed_script()`, `submit_customer_onboarding()` |
| `healing_router.py` | Error classification logic | `decide()`, `HEALABLE_ERRORS` set |
| `docker-compose.yml` | Service orchestration | Configure BOT_ID, ORCHESTRATOR_URL, HEARTBEAT_INTERVAL |
| `orchestrator-monitor/app.py` | Orchestrator API | `/heartbeat`, `/report_failure` endpoints |
| `rpa/run_healed_or_original.py` | Fallback launcher | Run healed or original script |

---

## Environment Variables You Control

```bash
# Bot Configuration
BOT_ID=DUMMY-BOT-new                              # Unique bot identifier
ORCHESTRATOR_URL=http://orchestrator_monitor:8000 # Where to send heartbeats/failures

# Heartbeat Settings
HEARTBEAT_INTERVAL_SECONDS=5                      # Check health every N seconds
HEARTBEAT_TIMEOUT_SECONDS=10                      # Give up if no response

# Healing Wait Settings
AUTO_WAIT_FOR_HEALING=true                        # Enable auto-recovery mode
HEALING_POLL_INTERVAL_SECONDS=3                   # Check for healed script every N seconds
HEALING_WAIT_TIMEOUT_SECONDS=600                  # Stop waiting after N seconds (10 min)

# Script Paths
HEALED_SCRIPTS_DIR=/app/healed_scripts            # Where to find healed scripts
```

---

## Viva Questions You Should Be Ready For

### Q1: "Explain your heartbeat monitoring system"
**A:** A non-daemon thread sends heartbeats every 5 seconds to the orchestrator's `/heartbeat` endpoint. If heartbeats stop, the orchestrator knows the bot failed. The thread stays alive until the bot crashes or completes, so we always have liveness detection.

### Q2: "How do you know which errors are fixable?"
**A:** We use a router that checks the error type against a `HEALABLE_ERRORS` set (ELEMENT_NOT_FOUND, TIMEOUT_ERROR, UI_SELECTOR_CHANGED, etc.). If the error is in this set AND we have the element's HTML, it's healable. Otherwise, we can't fix it.

### Q3: "What happens when a bot fails?"
**A:** We capture the failure (error message, page HTML, screenshot, locator, line number), send it to the orchestrator at `/report_failure`, the router classifies it, the healing engine patches the script, and we wait for the healed script to appear. Once found, we restart the bot process with the fixed version.

### Q4: "Why restart the process instead of just reloading the script?"
**A:** Because Playwright's sync API creates a single event loop per process. If we try to run nested Playwright code inside an active context, it crashes. Process restart via `os.execv()` launches a fresh Python interpreter with a new Playwright context, avoiding this nesting conflict.

### Q5: "How do you collect customer data?"
**A:** We have a global `submitted_records` array. Every time a customer form is submitted successfully, we create an `OnboardingRecord` object and append it to the array. At the end, we print all collected records with their details.

### Q6: "What if healing takes too long?"
**A:** We have a 600-second timeout. If the healed script doesn't appear within 10 minutes, we stop waiting and exit. This prevents the bot from hanging forever.

### Q7: "Can healing fail?"
**A:** Yes. If the healing engine is offline, if the error can't be fixed automatically, or if the PTQA service rejects the healing, we fall back to the original script. We also validate that healed scripts are created AFTER the failure timestamp to ensure we're using fresh fixes.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     DISTRIBUTED ORCHESTRATOR                     │
│                     (Your Implementation)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐        ┌──────────────────┐               │
│  │   Bot Instance   │        │  Orchestrator    │               │
│  │   (main.py)      │◄──────►│  (app.py)        │               │
│  │                  │        │                  │               │
│  │ • Heartbeat ◄────┼────────┼──► /heartbeat    │               │
│  │   Thread   │     │        │                  │               │
│  │            │     │        │                  │               │
│  │ • Failure  ├─────┼────────┼──► /report_      │               │
│  │   Report   │     │        │     failure      │               │
│  │            │     │        │                  │               │
│  │ • Wait &   │     │    ┌───┴──────────────┐   │               │
│  │   Restart  ├─────┼───►│ healing_router   │   │               │
│  │            │     │    │ .decide()        │   │               │
│  │ • Recover  │     │    └────┬─────────────┘   │               │
│  │   Logic    │     │         │                 │               │
│  └──────────┬─┘     │    ┌────┴─────────────────┐   │
│             │       │    │ Healing Engine       │   │
│             │       │    │ (AI Patcher)         │   │
│             │       │    └────┬──────────────────┘   │
│             │       │         │                 │
│             │       │    ┌────┴─────────────────┐
│             └───────┼───►│ Healed Script        │
│                     │    │ Detection & Restart  │
│                     │    └──────────────────────┘
│                     │                           │
└─────────────────────┼───────────────────────────┘
                      │
            ┌─────────▼──────────┐
            │ Data Collection    │
            │ submitted_records  │
            │ array              │
            └────────────────────┘
```

---

## Summary: Your Role

You built the **nervous system** of the RPA framework:

✅ **Heartbeat Monitoring** - Continuous health checks  
✅ **Failure Collection** - Rich context gathering  
✅ **Failure Routing** - Smart error classification  
✅ **Auto-Recovery** - Automatic restart with fixes  
✅ **Fallback Safety** - Never crash, always have a backup  
✅ **Multi-Bot Support** - Handle multiple instances  
✅ **Data Tracking** - Collect and report results  

This orchestrator is the **intelligence** that makes the RPA system **self-healing**.

---

**End of Viva Guide**
