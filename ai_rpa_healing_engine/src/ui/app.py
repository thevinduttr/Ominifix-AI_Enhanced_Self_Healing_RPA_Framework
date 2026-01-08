from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st

# ---- Fix ModuleNotFoundError: src ----
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.runner.heal import heal_one
from src.utils.path_manager import PathManager


st.set_page_config(page_title="Ominifix | Healing Engine", page_icon="🩹", layout="wide")

st.markdown(
    """
    <style>
      .card { border: 1px solid rgba(255,255,255,0.14); border-radius: 16px; padding: 16px;
              background: rgba(255,255,255,0.03); }
      .chip { display:inline-block; padding: 4px 10px; border-radius: 999px;
              border: 1px solid rgba(255,255,255,0.16); margin-right: 6px; font-size: 0.85rem; }
      .muted { opacity: 0.85; font-size: 0.9rem; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🩹 Ominifix — AI-Enhanced Code Healing Engine (PP1)")
st.caption(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Root: {PROJECT_ROOT}")

tabs = st.tabs(["🧩 Single Heal", "📦 Batch", "ℹ️ About"])

def read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p: Path, data: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def summarize(out_json: dict) -> dict:
    md = out_json.get("metadata", {})
    fc = out_json.get("failure_context", {})
    hs = out_json.get("healing_summary", {})
    so = out_json.get("script_output", {})
    mi = out_json.get("model_info", {})
    return {
        "status": hs.get("status"),
        "bot_id": md.get("bot_id"),
        "strategy_used": hs.get("strategy_used"),
        "model_conf": mi.get("confidence"),
        "action": fc.get("action"),
        "error_type": fc.get("error_type"),
        "old_locator": hs.get("old_locator") or fc.get("old_locator"),
        "new_locator": hs.get("new_locator"),
        "original_script": so.get("original_script_path"),
        "healed_script": so.get("healed_script_path"),
        "valid": (hs.get("validation") or {}).get("valid"),
        "reason": (hs.get("validation") or {}).get("reason"),
    }

def status_badge(status: str):
    s = (status or "").upper()
    if s == "SUCCESS":
        st.success("✅ SUCCESS")
    elif s == "FAILED":
        st.error("❌ FAILED")
    else:
        st.info("ℹ️ NO_FIX")

# -------------------------
# TAB 1: SINGLE HEAL
# -------------------------
with tabs[0]:
    left, right = st.columns([1.25, 1])

    with left:
        st.markdown("### Input")
        mode = st.radio("Input mode", ["Paste JSON", "Upload JSON", "Pick from folder"], horizontal=True)

        input_dict = None
        input_path = None

        if mode == "Paste JSON":
            st.markdown("<div class='muted'>Paste the ELR JSON input here.</div>", unsafe_allow_html=True)
            default_text = """{
  "metadata": {
    "report_id": "ELR-SLIIT-001",
    "run_id": "RUN-PP1-INT-01",
    "bot_id": "BOT-SLIIT-PDP-01",
    "timestamp": "2026-01-04T09:15:00",
    "source_component": "element_locator_engine",
    "target_component": "code_healing_engine"
  },
  "failure_context": {
    "script_path": "E:/RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/rpa_systems/sliit_pdp_rpa/src/extract/pdp_scraper.py",
    "failing_line": 31,
    "action": "wait_for_selector",
    "old_locator": "ul.nav.hr-tab-nav[role='tablist']",
    "error_type": "TIMEOUT_WAITING_FOR_SELECTOR",
    "error_message": "Timeout waiting for selector ul.nav.hr-tab-nav[role='tablist']"
  },
  "dom_context": {
    "page_url": "https://www.sliit.lk/professional-programmes/",
    "page_name": "SLIIT Professional Programmes",
    "new_element_html": "<ul class=\\"nav hr-tabs-nav nav-alignment--left clearfix\\" role=\\"tablist\\">...</ul>"
  },
  "element_expectation": {
    "expected_role": "tablist",
    "expected_text": "Online Programs"
  }
}"""
            raw = st.text_area("ELR Input JSON", value=default_text, height=360)
            if raw.strip():
                try:
                    input_dict = json.loads(raw)
                    st.success("JSON parsed OK.")
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")

        elif mode == "Upload JSON":
            up = st.file_uploader("Upload ELR input JSON", type=["json"])
            if up is not None:
                try:
                    input_dict = json.loads(up.read().decode("utf-8"))
                    st.success("Uploaded JSON loaded.")
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")

        else:
            inbox_root = PROJECT_ROOT / "data" / "inbox" / "elr_inputs"
            synthetic_root = PROJECT_ROOT / "data" / "synthetic_inputs"
            all_files = sorted(list(inbox_root.rglob("*.json")) + list(synthetic_root.rglob("*.json")))

            if not all_files:
                st.warning(f"No JSONs found under:\n- {inbox_root}\n- {synthetic_root}")
            else:
                sel = st.selectbox("Select input JSON", options=[str(p) for p in all_files])
                input_path = Path(sel)
                input_dict = read_json(input_path)
                st.success(f"Loaded: {input_path.name}")

        st.markdown("### Run")
        run = st.button("🚀 Run Healing", type="primary", use_container_width=True, disabled=(input_dict is None))

        show_input = st.toggle("Show input JSON", value=False)
        if show_input and input_dict:
            st.json(input_dict)

    with right:
        st.markdown("### Output")
        st.markdown("<div class='card'>", unsafe_allow_html=True)

        if run and input_dict:
            md = input_dict.get("metadata", {})
            bot_id = md.get("bot_id", "UNKNOWN_BOT")

            # Persist pasted/uploaded JSON into inbox so heal_one(Path) works consistently
            if input_path is None:
                day = datetime.now().strftime("%Y-%m-%d")
                ts = datetime.now().strftime("%Y%m%d--%H%M%S")
                inbox = PROJECT_ROOT / "data" / "inbox" / "elr_inputs" / bot_id / day
                inbox.mkdir(parents=True, exist_ok=True)
                input_path = inbox / f"ui_input--{ts}.json"
                write_json(input_path, input_dict)

            try:
                status = heal_one(input_path)

                pm = PathManager(bot_id)
                out_path = pm.healing_output_path()
                if not out_path.exists():
                    st.error("Healing completed but output JSON not found (check PathManager output location).")
                else:
                    out_json = read_json(out_path)
                    s = summarize(out_json)

                    status_badge(s["status"])
                    st.markdown(
                        f"""
                        <span class="chip">Bot: {s["bot_id"]}</span>
                        <span class="chip">Strategy: {s["strategy_used"]}</span>
                        <span class="chip">Model confidence: {s["model_conf"]}</span>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown("#### Decision")
                    st.write({
                        "action": s["action"],
                        "error_type": s["error_type"],
                        "old_locator": s["old_locator"],
                        "new_locator": s["new_locator"],
                    })

                    st.markdown("#### Files")
                    st.write({
                        "original_script": s["original_script"],
                        "healed_script": s["healed_script"],
                    })

                    st.markdown("#### Validation")
                    st.write({"valid": s["valid"], "reason": s["reason"]})

                    with st.expander("Full output JSON"):
                        st.json(out_json)

            except Exception as e:
                st.exception(e)

        else:
            st.caption("Provide input JSON and click **Run Healing**.")

        st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# TAB 2: BATCH
# -------------------------
with tabs[1]:
    st.markdown("### Batch Healing")
    inbox_default = PROJECT_ROOT / "data" / "inbox" / "elr_inputs"
    inbox_path = st.text_input("Inbox path", value=str(inbox_default))

    if st.button("⚙️ Run Batch", use_container_width=True):
        inbox = Path(inbox_path)
        files = sorted(inbox.rglob("*.json")) if inbox.exists() else []
        if not files:
            st.warning("No JSON inputs found in the inbox path.")
        else:
            ok = fail = nofix = 0
            for f in files:
                try:
                    s = heal_one(f)
                    if s == "SUCCESS": ok += 1
                    elif s == "FAILED": fail += 1
                    else: nofix += 1
                except Exception:
                    fail += 1
            st.success("Batch completed.")
            st.write({"SUCCESS": ok, "FAILED": fail, "NO_FIX": nofix})

# -------------------------
# TAB 3: ABOUT
# -------------------------
with tabs[2]:
    st.markdown("### Technologies used")
    st.markdown(
        """
- **Python** (core)
- **Playwright** (RPA runtime – scripts being healed)
- **scikit-learn** (Strategy Selection ML model)
- **TF-IDF / RandomForest / Logistic Regression** (strategy classifier options)
- **LibCST** (AST-safe script patching, formatting preserved)
- **Streamlit** (PP1 demo UI)
        """
    )

    st.markdown("### How the system works (PP1 explanation)")
    st.markdown(
        """
1) Receive ELR JSON with failure + DOM evidence  
2) ML model predicts healing strategy + confidence  
3) Locator generator creates best candidate locator from DOM snippet  
4) Patcher modifies only the failing selector in the script  
5) Validate the healed script  
6) Output JSON + healed script saved for Predictive Testing module
        """
    )

    st.markdown("### Run commands")
    st.code("streamlit run src/ui/app.py", language="bash")
    st.code("python -m src.runner.heal --inbox data/inbox/elr_inputs", language="bash")
