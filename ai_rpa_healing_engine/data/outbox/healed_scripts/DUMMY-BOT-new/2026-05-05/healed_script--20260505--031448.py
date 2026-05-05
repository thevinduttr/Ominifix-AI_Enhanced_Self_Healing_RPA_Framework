import os
import glob
import runpy
import sys
import threading
import time
from datetime import datetime, UTC
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

#url = "https://bank-system-for-rp-system.vercel.app/"
url ='http://localhost:5174/'
BOT_ID = os.getenv("BOT_ID", "DUMMY-BOT-new")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL") or os.getenv("MONITOR_URL", "http://localhost:8000")
ORCHESTRATOR_URL = ORCHESTRATOR_URL.removesuffix("/heartbeat")
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("HEARTBEAT_INTERVAL", "5"))
AUTO_WAIT_FOR_HEALING = os.getenv("AUTO_WAIT_FOR_HEALING", "true").strip().lower() in {"1", "true", "yes"}
HEALED_SCRIPTS_DIR = os.getenv("HEALED_SCRIPTS_DIR", "/app/healed_scripts").strip() or "/app/healed_scripts"
HEALING_POLL_INTERVAL_SECONDS = int(os.getenv("HEALING_POLL_INTERVAL_SECONDS", "3"))
HEALING_WAIT_TIMEOUT_SECONDS = int(os.getenv("HEALING_WAIT_TIMEOUT_SECONDS", "600"))
bot_running = True  # Flag to control heartbeat
submitted_records = []  # Array to collect customer onboarding records


def env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes"}


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


def send_failure_report(page, exc: Exception) -> None:
    """Send failure details to orchestrator."""
    try:
        page_url = page.url if page else "unknown"
        page_html = page.content() if page else ""

        # Use absolute path so healing engine can resolve script without RPA_ROOT.
        script_path = os.path.abspath(__file__)

        # Extract failing line from traceback if possible.
        failing_line = 1
        tb = exc.__traceback__
        while tb:
            if tb.tb_frame.f_code.co_filename == __file__:
                failing_line = tb.tb_lineno
            tb = tb.tb_next

        # Keep old locator aligned with the actual Playwright error string.
        error_text = str(exc)
        old_locator = ""
        if "Element not found:" in error_text:
            old_locator = error_text.split("Element not found:", 1)[1].strip()

        screenshot_path = ""
        try:
            os.makedirs("rpa", exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            screenshot_path = os.path.join("rpa", f"failure_{timestamp}.png")
            page.screenshot(path=screenshot_path, full_page=True)
        except Exception:
            pass

        failure_type = "ELEMENT_NOT_FOUND"
        if isinstance(exc, PlaywrightTimeoutError):
            failure_type = "TIMEOUT_ERROR"

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


def require_locator(page, selector: str):
    locator = page.locator(selector)
    if locator.count() == 0:
        raise Exception(f"Element not found: {selector}")
    return locator


def resolve_healed_scripts_dir(path_str: str) -> str:
    """Resolve healed script directory when running in or outside containers."""
    path = Path(path_str)
    if path.exists():
        return str(path)

    if path_str == "/app/healed_scripts":
        repo_root = Path(__file__).resolve().parents[2]
        mapped = repo_root / "ai_rpa_healing_engine" / "data" / "outbox" / "healed_scripts"
        if mapped.exists():
            return str(mapped)

    return path_str


def find_latest_healed_script(bot_id: str, min_mtime: float = 0.0) -> str:
    """Find latest healed script for the bot, optionally newer than min_mtime."""
    healed_root = Path(resolve_healed_scripts_dir(HEALED_SCRIPTS_DIR)) / bot_id
    if not healed_root.exists():
        return ""

    patterns = [
        str(healed_root / "*" / "healed_script--*.py"),
        str(healed_root / "healed_script--*.py"),
    ]

    candidates = []
    for pattern in patterns:
        candidates.extend(glob.glob(pattern))

    if not candidates:
        return ""

    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    for candidate in candidates:
        if os.path.getmtime(candidate) > min_mtime:
            return candidate
    return ""


def wait_and_run_healed_script(failed_at: float) -> bool:
    """Keep bot alive after failure, wait for healed script, and run it automatically."""
    if not AUTO_WAIT_FOR_HEALING:
        return False

    deadline = time.time() + HEALING_WAIT_TIMEOUT_SECONDS
    print(
        f" Waiting for healed script for {BOT_ID} (timeout={HEALING_WAIT_TIMEOUT_SECONDS}s, "
        f"poll={HEALING_POLL_INTERVAL_SECONDS}s). Browser session remains open."
    )

    while bot_running and time.time() < deadline:
        healed_script = find_latest_healed_script(BOT_ID, min_mtime=failed_at)
        if healed_script:
            print(f" Healed script detected: {healed_script}")
            print(" Restarting process to run healed script in a fresh Playwright context...")
            launcher_path = Path(__file__).resolve().parent / "rpa" / "run_healed_or_original.py"
            try:
                os.environ["FORCE_HEALED_SCRIPT_PATH"] = healed_script
                os.execv(sys.executable, [sys.executable, str(launcher_path)])
            except Exception as exec_err:
                print(f"⚠️ Failed to restart launcher: {exec_err}")
        time.sleep(HEALING_POLL_INTERVAL_SECONDS)

    print(" Healing wait timeout reached. Exiting failed run.")
    return False


def open_customers_page(page):
    """Navigate to the customer onboarding view."""
    try:
        page.locator("text=Customers").click()
    except Exception:
        page.goto(f"{url.rstrip('/')}/customers")
    page.wait_for_load_state("networkidle")


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
        {
            "fullname": "Priya Sharma",
            "segment": "Private",
            "customer_id": "NIC-199234567890",
            "gender": "Female",
            "branch": "Kandy Branch",
            "notes": "Premium tier customer.",
        },
        {
            "fullname": "Arun Devadas",
            "segment": "Retail",
            "customer_id": "NIC-198901234567",
            "gender": "Male",
            "branch": "Galle Branch",
            "notes": "Regular retail customer.",
        },
    ]


def fill_customer_onboarding_form(page, customer_data: dict) -> dict:
    """Fill the customer onboarding form fields that the bot should drive. Returns the data that was entered."""
    fullname_value = customer_data["fullname"]
    segment_value = customer_data["segment"]
    customer_id_value = customer_data["customer_id"]
    gender_value = customer_data["gender"]
    branch_value = customer_data["branch"]
    notes_value = customer_data["notes"]
    
    customer_fullname = require_locator(page, "#customer-fullna")
    customer_fullname.click()
    customer_fullname.fill("")
    customer_fullname.type(fullname_value, delay=100)
    page.wait_for_timeout(200)

    customer_segment = require_locator(page, "#customer-segment")
    customer_segment.select_option(label=segment_value)

    customer_id = require_locator(page, "#customer-id")
    customer_id.click()
    customer_id.fill("")
    customer_id.type(customer_id_value, delay=100)
    page.wait_for_timeout(200)

    gender_selector = f"input[name='customer-gender'][value='{gender_value}']"
    customer_gender = require_locator(page, gender_selector)
    customer_gender.check()

    assigned_branch = require_locator(page, "#assigned-branch")
    assigned_branch.click()
    assigned_branch.fill("")
    assigned_branch.type(branch_value, delay=100)
    page.wait_for_timeout(200)

    customer_terms = require_locator(page, "#customer-terms")
    terms_checked = False
    if not customer_terms.is_checked():
        customer_terms.check()
        terms_checked = True

    customer_notes = require_locator(page, "#customer-notes")
    customer_notes.click()
    customer_notes.fill("")
    customer_notes.type(notes_value, delay=100)
    
    return {
        "fullname": fullname_value,
        "segment": segment_value,
        "customer_id": customer_id_value,
        "gender": gender_value,
        "branch": branch_value,
        "notes": notes_value,
        "terms_accepted": terms_checked,
    }


def submit_customer_onboarding(page, customer_data: dict) -> None:
    """Fill and submit KYC for customer onboarding. Collects data into submitted_records array."""
    global submitted_records
    
    # Fill the form with customer data
    form_data = fill_customer_onboarding_form(page, customer_data)

    # Submit KYC (triggers dialog)
    page.once("dialog", lambda dialog: dialog.accept())
    submit_kyc = require_locator(page, "#submit-kyc")
    submit_kyc.click()
    
    # Collect the submitted record
    record = create_onboarding_record(
        fullname=form_data["fullname"],
        segment=form_data["segment"],
        customer_id=form_data["customer_id"],
        gender=form_data["gender"],
        branch=form_data["branch"],
        notes=form_data["notes"],
        terms_accepted=form_data["terms_accepted"],
    )
    submitted_records.append(record)
    print(f"✅ Record collected: {form_data['fullname']} ({form_data['segment']})")
    page.wait_for_timeout(1500)


def run():
    """Main bot execution."""
    global bot_running, submitted_records

    # Start heartbeat in background
    heartbeat_thread = threading.Thread(target=send_heartbeat)
    heartbeat_thread.start()
    print(f"🔄 Heartbeat thread started")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=env_flag("HEADLESS"), slow_mo=800)
            page = browser.new_page()

            page.goto(url)
            page.wait_for_load_state("networkidle")

            try:
                username_input = require_locator(page, "input[placeholder='admin']")
                username_input.fill("admin")

                password_input = require_locator(page, "input[placeholder='admin123']")
                password_input.fill("admin123")

                login_button = require_locator(page, "button[type='submit']")
                login_button.click()

                page.wait_for_load_state("networkidle")

                open_customers_page(page)

                # Get list of customers to onboard
                customers_to_add = get_customer_data_list()
                print(f"\n🚀 Starting to add {len(customers_to_add)} customers...\n")

                # Submit each customer
                for idx, customer_data in enumerate(customers_to_add, 1):
                    print(f"\n[{idx}/{len(customers_to_add)}] Adding customer: {customer_data['fullname']}")
                    submit_customer_onboarding(page, customer_data)
                    if idx < len(customers_to_add):
                        page.wait_for_timeout(2000)  # Wait before next customer

                page.wait_for_timeout(5000)

            except Exception as e:
                print(f" Bot execution failed: {e}")
                send_failure_report(page, e)

                failed_at = time.time()
                recovered = wait_and_run_healed_script(failed_at)
                if not recovered:
                    bot_running = False

            while bot_running:
                time.sleep(1)
    except KeyboardInterrupt:
        print(" Bot stopped by Ctrl+C")
    finally:
        bot_running = False
        heartbeat_thread.join()
        print(f"\n{'='*60}")
        print(f" Bot Execution Complete - Total Records: {len(submitted_records)}")
        print(f"{'='*60}")
        if submitted_records:
            print("\n Successfully Onboarded Customers:")
            for idx, record in enumerate(submitted_records, 1):
                print(f"  {idx}. {record['fullName']} (ID: {record['nationalId']}) - {record['segment']} - {record['stage']}")
            print(f"\n✨ All {len(submitted_records)} customers added successfully!")
        else:
            print("\n  No records collected.")


if __name__ == "__main__":
    run()
