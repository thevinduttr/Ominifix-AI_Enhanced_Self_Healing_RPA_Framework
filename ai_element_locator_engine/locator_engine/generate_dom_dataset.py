import os
import json
import time
from datetime import datetime

import joblib
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By

MODEL_PATH = os.path.join("data", "models", "dom_locator_model.pkl")
OUT_REPORT = os.path.join("data", "logs", "locator_report_pp1.json")
os.makedirs(os.path.dirname(OUT_REPORT), exist_ok=True)

def safe_attr(el, name: str) -> str:
    try:
        return el.get_attribute(name) or ""
    except Exception:
        return ""

def element_is_visible(el) -> bool:
    try:
        if not el.is_displayed():
            return False
        r = el.rect
        return r.get("width", 0) > 2 and r.get("height", 0) > 2
    except Exception:
        return False

def get_full_xpath(driver, el) -> str:
    js = r"""
    function fullXPath(el){
      if(!el || el.nodeType !== 1) return "";
      if(el === document.documentElement) return "/html";
      if(el === document.body) return "/html/body";
      let ix = 1;
      let sib = el.previousSibling;
      while(sib){
        if(sib.nodeType === 1 && sib.tagName === el.tagName) ix++;
        sib = sib.previousSibling;
      }
      return fullXPath(el.parentNode) + "/" + el.tagName.toLowerCase() + "[" + ix + "]";
    }
    return fullXPath(arguments[0]);
    """
    return driver.execute_script(js, el) or ""

def build_stable_xpath(tag: str, el_id: str, name: str, aria: str, placeholder: str, el_type: str) -> str:
    # Priority: id > name > aria-label > placeholder > type+tag fallback
    if el_id:
        return f"//*[@id='{el_id}']"
    if name:
        return f"//{tag}[@name='{name}']"
    if aria:
        return f"//{tag}[@aria-label='{aria}']"
    if placeholder:
        return f"//{tag}[@placeholder='{placeholder}']"
    if el_type and tag in ["input", "button"]:
        return f"//{tag}[@type='{el_type}']"
    return f"//{tag}"

def build_css_selector(tag: str, el_id: str, name: str, classes: str) -> str:
    if el_id:
        return f"#{el_id}"
    if name:
        return f"{tag}[name='{name}']"
    if classes:
        # pick first class only for stability
        c = classes.split()[0]
        return f"{tag}.{c}"
    return tag

def extract_candidates(driver):
    elems = driver.find_elements(By.CSS_SELECTOR, "button,a,input,select,textarea,[role='button']")
    out = []

    for el in elems:
        try:
            if not element_is_visible(el):
                continue

            tag = (el.tag_name or "").lower()
            el_type = (safe_attr(el, "type") or "").lower()
            text = (safe_attr(el, "innerText") or el.text or "").strip()

            el_id = safe_attr(el, "id")
            name = safe_attr(el, "name")
            classes = safe_attr(el, "class")
            aria = safe_attr(el, "aria-label")
            placeholder = safe_attr(el, "placeholder")

            # Skip empty-image anchors
            if tag == "a" and not (text or aria or name or el_id):
                continue

            fullxp = get_full_xpath(driver, el)
            stablexp = build_stable_xpath(tag, el_id, name, aria, placeholder, el_type)
            css = build_css_selector(tag, el_id, name, classes)

            out.append({
                # ML features
                "tag": tag,
                "type": el_type,
                "text_len": len(text),
                "has_id": int(bool(el_id)),
                "has_name": int(bool(name)),
                "has_class": int(bool(classes)),
                "has_aria": int(bool(aria)),
                "has_placeholder": int(bool(placeholder)),

                # used for expectation matching
                "text": text,
                "attrs_blob": (el_id + " " + name + " " + classes + " " + aria + " " + placeholder).lower(),

                # reporting
                "id": el_id,
                "name": name,
                "class": classes,
                "aria": aria,
                "placeholder": placeholder,
                "full_xpath": fullxp,
                "stable_xpath": stablexp,
                "css_selector": css,
                "outer_html": safe_attr(el, "outerHTML")
            })
        except Exception:
            continue

    return out

def run_dom_locator(failure_ctx: dict):
    pipeline = joblib.load(MODEL_PATH)

    driver = webdriver.Chrome()
    try:
        driver.get(failure_ctx["page_url"])
        time.sleep(2.5)

        candidates = extract_candidates(driver)
        if not candidates:
            raise RuntimeError("No candidates extracted.")

        expected_text = (failure_ctx.get("expected_text") or "").strip().lower()
        action = failure_ctx.get("failed_action", "")
        expected_role = failure_ctx.get("element_role", "")

        for c in candidates:
            c["action"] = action
            c["expected_role"] = expected_role
            c["expected_text_len"] = len(expected_text)
            c["expected_in_text"] = int(expected_text and expected_text in c["text"].lower())
            c["expected_in_attrs"] = int(expected_text and expected_text in c["attrs_blob"])

        df = pd.DataFrame(candidates)

        feature_cols = [
            "action","expected_role","expected_text_len",
            "tag","type","text_len",
            "has_id","has_name","has_class","has_aria","has_placeholder",
            "expected_in_text","expected_in_attrs"
        ]

        probs = pipeline.predict_proba(df[feature_cols])[:, 1]
        df["confidence"] = probs

        best = df.sort_values("confidence", ascending=False).iloc[0].to_dict()

        report = {
            "metadata": {
                "report_id": "ELR-PP1-001",
                "run_id": failure_ctx.get("metadata", {}).get("bot_id", "RUN-UNKNOWN"),
                "timestamp": datetime.now().isoformat(),
                "source_component": "element_locator_engine",
                "target_component": "code_healing_engine"
            },
            "failure_context": {
                "page_url": failure_ctx["page_url"],
                "action": action,
                "old_locator": failure_ctx.get("old_locator", ""),
                "error_type": failure_ctx.get("failure_type", ""),
                "error_message": failure_ctx.get("error_message", "Element not found")
            },
            "dom_context": {
                "page_url": failure_ctx["page_url"],
                "new_element_html": best["outer_html"],
                "recommended_locator": {
                    "stable_xpath": best["stable_xpath"],
                    "full_xpath": best["full_xpath"],
                    "css_selector": best["css_selector"]
                },
                "element_attributes": {
                    "tag": best["tag"],
                    "type": best["type"],
                    "id": best["id"],
                    "name": best["name"],
                    "aria": best["aria"],
                    "placeholder": best["placeholder"]
                }
            },
            "element_expectation": {
                "expected_role": expected_role,
                "expected_text": failure_ctx.get("expected_text")
            },
            "resolution": {
                "status": "success",
                "confidence": float(best["confidence"])
            }
        }

        with open(OUT_REPORT, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        print("[OK] Report saved:", OUT_REPORT)
        print("[BEST] stable_xpath:", best["stable_xpath"])
        print("[BEST] full_xpath:", best["full_xpath"])
        print("[BEST] css_selector:", best["css_selector"])
        print("[CONF]:", best["confidence"])
        return report

    finally:
        driver.quit()

if __name__ == "__main__":
    # Test 1: herokuapp login
    failure_ctx = {
        "page_url": "https://the-internet.herokuapp.com/login",
        "failure_type": "ElementNotFound",
        "failed_action": "click",
        "element_role": "primary_action",
        "expected_text": "Login",
        "metadata": {"bot_id": "RPA-0012"}
    }
    run_dom_locator(failure_ctx)
