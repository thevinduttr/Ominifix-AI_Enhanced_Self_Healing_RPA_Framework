from flask import Flask, render_template, redirect, url_for, request
import json
import os
import glob

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

UI_DIR = os.path.join(ROOT, "ui")
TEMPLATES_DIR = os.path.join(UI_DIR, "templates")
STATIC_DIR = os.path.join(UI_DIR, "static")

from locator_engine.run_dom_locator import run_dom_locator

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)

REPORT_PATH = os.path.join(ROOT, "data", "logs", "locator_report.json")


def load_latest_report():
    if os.path.exists(REPORT_PATH):
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


@app.route("/", methods=["GET"])
def dashboard():
    report = load_latest_report()
    return render_template("dashboard.html", report=report, title="Dashboard")


@app.route("/run-demo", methods=["POST"])
def run_demo():
    # UI inputs
    page_url = request.form.get("page_url")
    failure_type = request.form.get("failure_type", "ELEMENT_NOT_FOUND")
    failed_action = request.form.get("failed_action", "click")
    element_role = request.form.get("element_role", "primary_action")
    expected_text = request.form.get("expected_text", "")
    old_locator = request.form.get("old_locator", "")  # ✅ included

    bot_id = request.form.get("bot_id", "RPA-0012")
    workflow_step = request.form.get("workflow_step", "step_unknown")

    # optional real-world fields
    script_path = request.form.get("script_path", "data/scripts/broken/demo_flow.py")
    failing_line = request.form.get("failing_line", "18")

    failure_ctx = {
        "page_url": page_url,
        "failure_type": failure_type,
        "failed_action": failed_action,
        "element_role": element_role,
        "expected_text": expected_text,
        "old_locator": old_locator,  # ✅ MUST
        "error_message": "Timeout exceeded while waiting for selector",

        "script_path": script_path,
        "failing_line": failing_line,

        "metadata": {
            "bot_id": bot_id,
            "workflow_step": workflow_step
        }
    }

    run_dom_locator(failure_ctx)
    return redirect(url_for("view_report"))


@app.route("/report", methods=["GET"])
def view_report():
    report = load_latest_report()
    if not report:
        return redirect(url_for("dashboard"))

    raw_json = json.dumps(report, indent=2)
    return render_template("report.html", report=report, raw_json=raw_json, title="Locator Report")


@app.route("/history", methods=["GET"])
def history():
    logs_dir = os.path.join(ROOT, "data", "logs")
    reports = []
    for path in sorted(glob.glob(os.path.join(logs_dir, "locator_report_*.json")), reverse=True)[:10]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                reports.append(json.load(f))
        except Exception:
            continue

    return render_template("history.html", reports=reports, title="History")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
