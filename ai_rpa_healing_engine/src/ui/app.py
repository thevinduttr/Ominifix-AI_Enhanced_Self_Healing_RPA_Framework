import sys
import json
import time
from pathlib import Path

import streamlit as st

# --- Make `src.*` imports work in Streamlit ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.locator_gen.locator_generator import LocatorGenerator
from src.patcher.libcst_patcher import ScriptPatcher
from src.engine.healing_validator import HealingValidator
from src.ml.strategy_predictor import StrategyPredictor


# -------------------------
# CONFIG
# -------------------------
APP_TITLE = "Omnifix – Code Healing Engine"
APP_SUBTITLE = "AI-Enhanced Self-Healing RPA (Standalone Prototype Module)"
MODEL_PATH = "models/strategy_selector_v1.pkl"

DEFAULT_SAMPLE = "data/synthetic_inputs/elr_input_search_01.json"
SYNTHETIC_ROOT = Path("data/synthetic_inputs")
BATCH_DIR = Path("data/synthetic_inputs/batch")
UI_OUT_DIR = Path("data/ui_outputs")


# -------------------------
# UTILS
# -------------------------
def safe_mkdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def shorten(text: str, n: int = 1100) -> str:
    t = (text or "").strip()
    return t if len(t) <= n else t[:n] + "..."


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def list_inputs() -> list[str]:
    """
    Professional behavior:
    - Prefer curated JSONs under data/synthetic_inputs/* (including subfolders).
    - Include default + batch if available.
    """
    candidates: list[str] = []

    # Any json under synthetic_inputs (one level deep + nested)
    if SYNTHETIC_ROOT.exists():
        for p in sorted(SYNTHETIC_ROOT.rglob("*.json")):
            # avoid output folders if user accidentally places them there
            if "synthetic_outputs" in str(p).replace("\\", "/"):
                continue
            candidates.append(str(p).replace("\\", "/"))

    # Ensure DEFAULT_SAMPLE is present if exists
    if Path(DEFAULT_SAMPLE).exists() and DEFAULT_SAMPLE not in candidates:
        candidates.insert(0, DEFAULT_SAMPLE)

    # (Optional) Put batch files after others (but still available)
    if BATCH_DIR.exists():
        for p in sorted(BATCH_DIR.glob("elr_input_*.json"))[:50]:
            sp = str(p).replace("\\", "/")
            if sp not in candidates:
                candidates.append(sp)

    # Deduplicate preserving order
    seen = set()
    out = []
    for x in candidates:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def load_input(choice: str, uploaded) -> dict | None:
    if uploaded is not None:
        try:
            return json.loads(uploaded.getvalue().decode("utf-8"))
        except Exception as e:
            st.error(f"Uploaded JSON is invalid: {e}")
            return None

    if choice and Path(choice).exists():
        return read_json(Path(choice))

    return None


def inject_css():
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2.5rem; padding-bottom: 3.0rem; }
        [data-testid="stHeader"] { background: rgba(0,0,0,0); }

        /* Softer tab styling */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            height: 40px;
            padding: 0 14px;
            border-radius: 14px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
        }
        .stTabs [aria-selected="true"] {
            background: rgba(255,255,255,0.08) !important;
            border: 1px solid rgba(255,255,255,0.16) !important;
        }

        /* Small pill badges */
        .pill {
            display:inline-flex; gap:8px; align-items:center;
            padding:6px 10px; border-radius:999px;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.10);
            font-size: 13px;
        }
        .pill span.k { opacity:0.75; }
        .pill span.v { font-weight:650; }
        </style>
        """,
        unsafe_allow_html=True
    )


def pill(label: str, value: str):
    st.markdown(
        f"""<div class="pill"><span class="k">{label}</span><span class="v">{value}</span></div>""",
        unsafe_allow_html=True,
    )


def stage_item(title: str, status: str, detail: str):
    """
    status: "DONE" | "RUNNING" | "WARN" | "IDLE"
    """
    icon = {"DONE": "✅", "RUNNING": "⏳", "WARN": "⚠️", "IDLE": "—"}.get(status, "—")
    st.markdown(
        f"""
        <div style="
            display:flex; justify-content:space-between; align-items:center;
            padding:10px 12px; border-radius:14px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.09);
            margin-bottom:8px;
        ">
            <div style="display:flex; gap:10px; align-items:center;">
                <div style="font-size:18px">{icon}</div>
                <div>
                    <div style="font-weight:650; font-size:14px">{title}</div>
                    <div style="opacity:0.75; font-size:12px">{detail}</div>
                </div>
            </div>
            <div style="opacity:0.85; font-size:12px; font-weight:650">{status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def run_healing(inp: dict) -> dict:
    """
    End-to-end execution:
      1) Strategy prediction (ML)
      2) Locator regeneration from DOM snippet
      3) Format-preserving patch via LibCST (fill/click)
      4) Validation (compile)
      5) Output artifacts for downstream consumption
    """
    t0 = time.time()

    bot_id = inp["metadata"]["bot_id"]
    fc = inp["failure_context"]
    dc = inp["dom_context"]

    action = (fc.get("action") or "fill").strip().lower()  # fill | click
    script_path = fc["script_path"]
    failing_line = int(fc["failing_line"])
    old_locator = fc["old_locator"]
    error_type = fc["error_type"]
    element_html = dc.get("new_element_html", "")

    locator_gen = LocatorGenerator()
    patcher = ScriptPatcher()
    validator = HealingValidator()
    predictor = StrategyPredictor(MODEL_PATH)

    prediction = predictor.predict(
        error_type=error_type,
        old_locator=old_locator,
        element_html=element_html
    )

    out_dir = UI_OUT_DIR / bot_id
    safe_mkdir(out_dir)

    candidates = locator_gen.generate_candidates(element_html)
    best = locator_gen.pick_best(candidates)

    # No candidates => safe termination (NO_FIX)
    if not best:
        out_json = {
            "metadata": {
                "healing_id": "HEAL-UI-NOFIX",
                "bot_id": bot_id,
                "source_component": "code_healing_engine",
                "target_component": "predictive_testing_engine"
            },
            "healing_summary": {
                "status": "NO_FIX",
                "strategy_used": "NO_FIX",
                "action": action,
                "old_locator": old_locator,
                "new_locator": "",
                "confidence": 0.0,
                "patcher": "LibCST (format preserved)",
                "validation": {"valid": True, "reason": "Insufficient DOM/context; patch not attempted."}
            },
            "model_info": {
                "model_used": "strategy_selector_v1",
                "model_source": "kaggle",
                "predicted_strategy": prediction.label,
                "model_confidence": prediction.confidence
            },
            "runtime": {"duration_ms": int((time.time() - t0) * 1000)}
        }

        out_path = out_dir / "healing_output.json"
        out_path.write_text(json.dumps(out_json, indent=2), encoding="utf-8")

        return {
            "status": "NO_FIX",
            "bot_id": bot_id,
            "action": action,
            "error_type": error_type,
            "script_path": script_path,
            "failing_line": failing_line,
            "old_locator": old_locator,
            "element_html": element_html,
            "prediction": prediction,
            "best": None,
            "new_locator": "",
            "candidate_score": 0,
            "patch_result": None,
            "validation": out_json["healing_summary"]["validation"],
            "healed_script_path": "",
            "output_json_path": str(out_path),
            "duration_ms": out_json["runtime"]["duration_ms"],
        }

    new_locator = best["value"]
    score = best.get("score", 0)

    healed_script_path = out_dir / "healed_script.py"
    patch_result = patcher.patch_locator(
        script_path=script_path,
        output_path=str(healed_script_path),
        failing_line=failing_line,
        old_locator=old_locator,
        new_locator=new_locator,
        action=action,  # supports fill/click
    )

    if patch_result.status != "SUCCESS":
        out_json = {
            "metadata": {"healing_id": "HEAL-UI-FAIL", "bot_id": bot_id},
            "healing_summary": {
                "status": "FAILED",
                "strategy_used": prediction.label,
                "action": action,
                "old_locator": old_locator,
                "new_locator": new_locator,
                "confidence": score / 100.0,
                "patcher": "LibCST (format preserved)",
                "validation": {"valid": False, "reason": patch_result.message}
            },
            "model_info": {
                "model_used": "strategy_selector_v1",
                "model_source": "kaggle",
                "predicted_strategy": prediction.label,
                "model_confidence": prediction.confidence
            },
            "runtime": {"duration_ms": int((time.time() - t0) * 1000)}
        }
        out_path = out_dir / "healing_output.json"
        out_path.write_text(json.dumps(out_json, indent=2), encoding="utf-8")

        return {
            "status": "FAILED",
            "bot_id": bot_id,
            "action": action,
            "error_type": error_type,
            "script_path": script_path,
            "failing_line": failing_line,
            "old_locator": old_locator,
            "element_html": element_html,
            "prediction": prediction,
            "best": best,
            "new_locator": new_locator,
            "candidate_score": score,
            "patch_result": patch_result,
            "validation": out_json["healing_summary"]["validation"],
            "healed_script_path": "",
            "output_json_path": str(out_path),
            "duration_ms": out_json["runtime"]["duration_ms"],
        }

    validation = validator.validate_script(patch_result.healed_script_path)

    out_json = {
        "metadata": {
            "healing_id": "HEAL-UI-001",
            "bot_id": bot_id,
            "source_component": "code_healing_engine",
            "target_component": "predictive_testing_engine"
        },
        "healing_summary": {
            "status": "SUCCESS" if validation["valid"] else "FAILED",
            "strategy_used": prediction.label,
            "action": action,
            "old_locator": old_locator,
            "new_locator": new_locator,
            "confidence": score / 100.0,
            "patcher": "LibCST (format preserved)",
            "validation": validation
        },
        "locator_candidate": {"type": best.get("type"), "score": score},
        "script_output": {
            "original_script_path": script_path,
            "healed_script_path": patch_result.healed_script_path
        },
        "model_info": {
            "model_used": "strategy_selector_v1",
            "model_source": "kaggle",
            "predicted_strategy": prediction.label,
            "model_confidence": prediction.confidence
        },
        "runtime": {"duration_ms": int((time.time() - t0) * 1000)}
    }

    out_path = out_dir / "healing_output.json"
    out_path.write_text(json.dumps(out_json, indent=2), encoding="utf-8")

    return {
        "status": out_json["healing_summary"]["status"],
        "bot_id": bot_id,
        "action": action,
        "error_type": error_type,
        "script_path": script_path,
        "failing_line": failing_line,
        "old_locator": old_locator,
        "element_html": element_html,
        "prediction": prediction,
        "best": best,
        "new_locator": new_locator,
        "candidate_score": score,
        "patch_result": patch_result,
        "validation": validation,
        "healed_script_path": patch_result.healed_script_path if validation["valid"] else "",
        "output_json_path": str(out_path),
        "duration_ms": out_json["runtime"]["duration_ms"],
    }


# -------------------------
# UI
# -------------------------
def main():
    st.set_page_config(page_title="Omnifix – Code Healing Engine", page_icon="🛠️", layout="wide")
    inject_css()
    safe_mkdir(UI_OUT_DIR)

    # Header (clean)
    header_left, header_right = st.columns([1.6, 1.45], gap="large")
    with header_left:
        st.markdown(f"## {APP_TITLE}")
        st.markdown(f"<div style='opacity:0.82; font-size:15px'>{APP_SUBTITLE}</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        pill("Module", "Healing Engine")
        st.markdown("<span style='display:inline-block;width:10px'></span>", unsafe_allow_html=True)
        pill("Model", "Strategy Selector v1")
        st.markdown("<span style='display:inline-block;width:10px'></span>", unsafe_allow_html=True)
        pill("Patching", "LibCST (format preserved)")

    with header_right:
        st.markdown(
            """
            <div style="
                padding:25px 16px; border-radius:18px;
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.09);
            ">
                <div style="font-weight:700; font-size:18px">Module Objective</div>
                <div style="opacity:0.80; font-size:14.5px; margin-top:6px; line-height:1.5">
                    Autonomously recover broken RPA scripts by regenerating robust locators from DOM context,
                    patching scripts without formatting loss, validating outputs, and producing machine-consumable results.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("Input")
        inputs = list_inputs()
        choice = st.selectbox("Select input JSON", options=inputs if inputs else ["(no inputs found)"])
        uploaded = st.file_uploader("Upload JSON", type=["json"])

        st.divider()
        st.subheader("Runtime")
        st.write("**Model:**", f"`{MODEL_PATH}`")
        st.write("**Outputs:**", "`data/ui_outputs/<bot_id>/`")
        st.caption("This UI executes the standalone healing module end-to-end.")

    inp = load_input("" if "(no inputs found)" in choice else choice, uploaded)

    # Main layout
    left, right = st.columns([1.6, 1.45], gap="large")

    # Left: Input context + pipeline stages
    with left:
        st.markdown("### Input Context")
        if not inp:
            st.info("Select an input JSON or upload one to proceed.")
        else:
            fc = inp.get("failure_context", {})
            dc = inp.get("dom_context", {})

            m1, m2, m3 = st.columns(3)
            m1.metric("bot_id", inp["metadata"].get("bot_id", ""))
            m2.metric("action", fc.get("action", ""))
            m3.metric("error_type", fc.get("error_type", ""))

            st.markdown(
                f"""
                <div style="
                    padding:12px 14px; border-radius:18px;margin-bottom:10px;
                    background: rgba(255,255,255,0.04);
                    border: 1px solid rgba(255,255,255,0.09);
                ">
                    <div style="font-weight:700; font-size:13px; margin-bottom:6px">Failure Details</div>
                    <div style="font-size:12.5px; opacity:0.88; line-height:1.55">
                        <b>Old locator</b>: <code>{fc.get('old_locator','')}</code><br/>
                        <b>Script path</b>: <code>{fc.get('script_path','')}</code><br/>
                        <b>Failing line</b>: <code>{fc.get('failing_line','')}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander("DOM snippet", expanded=False):
                st.code(shorten(dc.get("new_element_html", ""), 1400), language="html")

            with st.expander("Full input JSON", expanded=False):
                st.json(inp)

        st.markdown("### Execution Pipeline")
        if "latest_run" not in st.session_state:
            st.session_state.latest_run = None

        if st.session_state.latest_run is None:
            stage_item("1) Strategy prediction (ML)", "IDLE", "Selects a healing strategy and confidence score")
            stage_item("2) Locator regeneration", "IDLE", "Generates candidate locators from DOM snippet")
            stage_item("3) Format-preserving patch", "IDLE", "Patches page.fill/page.click via LibCST")
            stage_item("4) Validation", "IDLE", "Validates healed script (compile)")
            stage_item("5) Output artifacts", "IDLE", "Writes healed script and result JSON")
        else:
            r = st.session_state.latest_run
            stage_item("1) Strategy prediction (ML)", "DONE", f"{r['prediction'].label} | conf={r['prediction'].confidence:.3f}")
            stage_item("2) Locator regeneration", "DONE" if r["best"] else "WARN", "Best candidate selected" if r["best"] else "No candidates (safe termination)")
            stage_item(
                "3) Format-preserving patch",
                "DONE" if (r["patch_result"] and r["patch_result"].status == "SUCCESS") else ("WARN" if r["status"] != "SUCCESS" else "WARN"),
                "LibCST preserves blank lines and structure"
            )
            stage_item("4) Validation", "DONE" if r["validation"]["valid"] else "WARN", r["validation"]["reason"])
            stage_item("5) Output artifacts", "DONE", Path(r["output_json_path"]).name)

    # Right: Run + Results
    with right:
        st.markdown("### Run")
        run_btn = st.button("Run Healing", type="primary", use_container_width=True, disabled=(inp is None))

        if "history" not in st.session_state:
            st.session_state.history = []

        if run_btn and inp:
            with st.spinner("Executing..."):
                res = run_healing(inp)
            st.session_state.latest_run = res
            st.session_state.history.insert(0, res)
            st.session_state.history = st.session_state.history[:6]

        if not st.session_state.history:
            st.info("Execute the module to view results.")
            return

        res = st.session_state.history[0]

        # KPI row
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Status", res["status"])
        k2.metric("Action", res["action"])
        k3.metric("Duration (ms)", res["duration_ms"])
        k4.metric("Model confidence", f"{res['prediction'].confidence:.2f}")

        tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Healed Script", "Output JSON", "Model"])

        with tab1:
            st.markdown("#### Summary")
            st.write(f"**Old locator:** `{res['old_locator']}`")
            st.write(f"**New locator:** `{res['new_locator']}`" if res["new_locator"] else "**New locator:** *(none)*")

            if res["best"]:
                st.write(f"**Candidate:** `{res['best'].get('type')}` | score `{res['candidate_score']}/100`")
            else:
                st.warning("No candidates available from the provided DOM snippet. The module terminated safely.")

            st.markdown("#### Patch & Validation")
            if res["patch_result"] is None:
                st.info("Patch not attempted.")
            else:
                st.write(f"**Patch result:** `{res['patch_result'].status}`")
                st.write("**Formatting preserved:** ✅")
            st.write(f"**Validation:** `{res['validation']}`")

        with tab2:
            healed_path = Path(res["healed_script_path"]) if res["healed_script_path"] else None
            if healed_path and healed_path.exists():
                code = healed_path.read_text(encoding="utf-8").splitlines()
                st.code("\n".join(code[:140]), language="python")

                st.download_button(
                    "Download healed_script.py",
                    data=healed_path.read_bytes(),
                    file_name=f"{res['bot_id']}_healed.py",
                    mime="text/x-python",
                    use_container_width=True,
                )
            else:
                st.warning("Healed script is not available.")

        with tab3:
            out_path = Path(res["output_json_path"])
            if out_path.exists():
                payload = read_json(out_path)
                st.json(payload)

                st.download_button(
                    "Download healing_output.json",
                    data=out_path.read_bytes(),
                    file_name=f"{res['bot_id']}_healing_output.json",
                    mime="application/json",
                    use_container_width=True,
                )
            else:
                st.warning("Output JSON not found.")

        with tab4:
            st.markdown("#### Strategy Model")
            st.write("**Model path:**", f"`{MODEL_PATH}`")
            st.write("**Predicted strategy:**", f"`{res['prediction'].label}`")
            st.write("**Confidence:**", f"{res['prediction'].confidence:.4f}")
            st.caption("Model trained externally and loaded locally for inference.")

        with st.expander("Recent executions", expanded=False):
            for i, h in enumerate(st.session_state.history, start=1):
                st.write(
                    f"{i}. `{h['bot_id']}` | `{h['action']}` | `{h['status']}` | "
                    f"`{h['prediction'].label}` ({h['prediction'].confidence:.3f})"
                )


if __name__ == "__main__":
    main()
