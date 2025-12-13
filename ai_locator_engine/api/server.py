from flask import Flask, render_template, redirect, url_for
import json
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

TEMPLATES_DIR = os.path.join(ROOT, "templates")
STATIC_DIR = os.path.join(ROOT, "static")

from orchestrator_sim.simulate_failure import run_bot_and_capture_failure
from locator_engine.fallback_logic import run_locator_engine

app = Flask(
    __name__, 
    template_folder=TEMPLATES_DIR, 
    static_folder=STATIC_DIR
)

@app.route("/")
def dashboard():
    """
    Landing page – simple description + a button to run the full demo.
    """
    # Check if there is an existing report
    report_path = os.path.join("data", "logs", "locator_report_pp1.json")
    report = None
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    return render_template("dashboard.html", report=report)


@app.route("/run-demo")
def run_demo():
    """
    Orchestrator simulation + locator engine execution.
    """
    # 1) Simulate bot failure (orchestrator side)
    failure_ctx = run_bot_and_capture_failure()

    # 2) Run locator engine
    report = run_locator_engine(failure_ctx)

    # 3) Redirect to report view
    return redirect(url_for("view_report"))


@app.route("/report")
def view_report():
    """
    Show the latest locator report in a nice UI.
    """
    report_path = os.path.join("data", "logs", "locator_report_pp1.json")
    if not os.path.exists(report_path):
        return redirect(url_for("dashboard"))

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    # flatten candidates to show in table
    candidates = report.get("candidates", [])
    best = report.get("best_locator")

    # also render raw JSON as pretty string
    raw_json = json.dumps(report, indent=2)

    return render_template(
        "report.html",
        report=report,
        best=best,
        candidates=candidates,
        raw_json=raw_json
    )


if __name__ == "__main__":
    # For demo/PP1 only – in production you'd use gunicorn etc.
    app.run(host="127.0.0.1", port=5000, debug=True)
