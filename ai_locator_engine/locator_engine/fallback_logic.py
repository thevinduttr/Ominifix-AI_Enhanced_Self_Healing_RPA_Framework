import os
from typing import Dict, List
from .dom_locator import extract_dom_candidates
from .feature_extractor import candidate_to_features
from .ml_scorer import score_candidate
from .report_builder import build_report
from .cv_locator import load_images, find_template_orb, estimate_element_screen_distance

def run_locator_engine(failure_context: Dict):
    html_path = failure_context["html_snapshot_path"]
    screenshot_path = failure_context["screenshot_path"]
    page_url = failure_context["page_url"]

    # 1. DOM candidates from HTML snapshot
    dom_candidates = extract_dom_candidates(
        html_path,
        element_role=failure_context.get("element_role"),
        expected_text=failure_context.get("expected_text")
    )

    # 2. CV info (for now we compute once per page)
    template_path = os.path.join("data", "templates", "login_button_template.png")
    cv_info = {"similarity": 0.0, "distance": 1000.0}

    if os.path.exists(template_path) and os.path.exists(screenshot_path):
        page_img, tmpl = load_images(screenshot_path, template_path)
        if page_img is not None and tmpl is not None:
            center, sim = find_template_orb(page_img, tmpl)
            if center is not None:
                cv_info["similarity"] = sim
                # for PP1, we don't map candidate bounding boxes exactly,
                # we just treat closer = better and approximate distance feature
                cv_info["distance"] = 100.0  # simplified for now

    # 3. For each candidate -> features -> ML confidence
    ranked = []
    for cand in dom_candidates:
        features, names = candidate_to_features(cand, failure_context, cv_info)
        conf = score_candidate(features)
        cand_with_conf = cand.copy()
        cand_with_conf["confidence"] = conf
        ranked.append(cand_with_conf)

    ranked.sort(key=lambda x: x["confidence"], reverse=True)

    # 4. Build report
    report, path = build_report(page_url, failure_context, ranked)
    print("[+] Locator report written to", path)
    return report
