import json
import os

def build_report(page_url, failure_context, ranked_candidates):
    report = {
        "page_url": page_url,
        "element_role": failure_context.get("element_role"),
        "expected_text": failure_context.get("expected_text"),
        "best_locator": None,
        "candidates": ranked_candidates,
        "analysis_notes": "DOM + CV + ML ranking executed."
    }

    if ranked_candidates:
        best = ranked_candidates[0]
        report["best_locator"] = {
            "long_xpath": best.get("long_xpath"),
            "tag": best.get("tag"),
            "text": best.get("text"),
            "confidence": best.get("confidence")
        }

    os.makedirs(os.path.join("data", "logs"), exist_ok=True)
    out_path = os.path.join("data", "logs", "locator_report_pp1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report, out_path
