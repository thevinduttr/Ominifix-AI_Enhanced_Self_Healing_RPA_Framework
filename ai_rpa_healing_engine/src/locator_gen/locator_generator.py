from typing import Any, Dict, List, Optional
import re

from bs4 import BeautifulSoup, Tag


class LocatorGenerator:
    """
    Generates RAW locator candidates from an HTML element snippet **or** a
    full-page DOM document.

    IMPORTANT:
      - Candidates returned here MUST be RAW selectors (NO wrapping quotes).
      - Quoting for Python code is handled later by the patcher.

    When the input is a full-page HTML document (contains ``<html`` or starts
    with ``<!DOCTYPE``), the generator extracts all interactable elements
    (buttons, inputs, links, forms, selects, textareas) and generates
    candidates from each.  ``element_expectation`` (expected_text /
    expected_role) is used to boost elements that match.
    """

    IMPORTANT_ATTRS = ["id", "name", "aria-label", "placeholder", "type", "role", "title"]

    # Tags considered "interactable" when scanning a full-page DOM
    _INTERACTABLE_TAGS = {
        "a", "button", "input", "select", "textarea", "form",
        "label", "option", "details", "summary", "dialog",
    }

    # ------------------------------------------------------------------ public

    def generate_candidates(
        self,
        element_html: str,
        expected_text: str = "",
        expected_role: str = "",
    ) -> List[Dict[str, Any]]:
        if not element_html or not element_html.strip():
            return []

        # Detect full-page HTML (vs. a single-element snippet)
        trimmed = element_html.strip()[:200].lower()
        is_full_page = (
            trimmed.startswith("<!doctype")
            or re.search(r"<html[\s>]", trimmed) is not None
        )

        if is_full_page:
            return self._candidates_from_full_dom(element_html, expected_text, expected_role)

        # ---------- Single element snippet (original path) ----------
        return self._candidates_from_snippet(element_html)

    # --------------------------------------------------------- single snippet

    def _candidates_from_snippet(self, element_html: str) -> List[Dict[str, Any]]:
        """Generate candidates from a single HTML element snippet."""
        soup = BeautifulSoup(element_html, "html.parser")
        el = soup.find(True)  # first real tag
        if not el or not el.name:
            return []
        return self._dedup(self._candidates_for_element(el))

    # ----------------------------------------------------------- full-page DOM

    def _candidates_from_full_dom(
        self,
        page_html: str,
        expected_text: str = "",
        expected_role: str = "",
    ) -> List[Dict[str, Any]]:
        """Extract interactable elements from a full page and generate candidates."""
        soup = BeautifulSoup(page_html, "html.parser")

        # Collect interactable elements that have at least one useful attribute
        elements: list[Tag] = []
        for tag_name in self._INTERACTABLE_TAGS:
            elements.extend(soup.find_all(tag_name))

        # Also grab ANY element with an id attribute (high value targets)
        for el in soup.find_all(True, attrs={"id": True}):
            if el not in elements and el.name not in ("html", "head", "body", "script", "style", "link", "meta"):
                elements.append(el)

        if not elements:
            # Fallback: try the old single-element path on the raw HTML
            return self._candidates_from_snippet(page_html)

        # Generate candidates from ALL interactable elements
        all_candidates: list[dict] = []
        any_expectation_match = False

        for el in elements:
            el_candidates = self._candidates_for_element(el)
            # Boost candidates that match expected_text or expected_role
            if expected_text or expected_role:
                el_text = (el.get_text(strip=True) or "").lower()
                el_role = (el.attrs.get("role", "") if isinstance(el.attrs.get("role"), str)
                           else " ".join(el.attrs.get("role", []))).lower()
                el_tag = el.name.lower()

                text_match = expected_text and expected_text.lower() in el_text
                role_match = expected_role and (
                    expected_role.lower() in el_role
                    or expected_role.lower() in el_tag
                )

                if text_match or role_match:
                    any_expectation_match = True
                    boost = 10 if (text_match and role_match) else 5
                    for c in el_candidates:
                        c["score"] = min(c["score"] + boost, 100)

            all_candidates.extend(el_candidates)

        # Generate Playwright text/role-based locators from element_expectation.
        # These target what the caller EXPECTS to find on the page.
        # If no DOM element matched: score 102 (override random IDs).
        # If a DOM element matched: score 85 (lower-priority alternative).
        expectation_score = 102 if not any_expectation_match else 85

        if expected_text:
            all_candidates.append({
                "type": "css",
                "value": f"text={expected_text}",
                "score": expectation_score,
            })
        if expected_role:
            # Map common role names to Playwright role selectors
            role_val = expected_role.strip().lower().replace("_", "")
            role_map = {
                "button": "button", "link": "link", "textbox": "textbox",
                "checkbox": "checkbox", "radio": "radio", "heading": "heading",
                "dialog": "dialog", "alert": "alert", "navigation": "navigation",
                "searchbox": "searchbox", "validationelement": "alert",
                "input": "textbox", "submitbutton": "button",
            }
            pw_role = role_map.get(role_val, "")
            if pw_role and expected_text:
                all_candidates.append({
                    "type": "css",
                    "value": f'role={pw_role}[name="{expected_text}"]',
                    "score": expectation_score - 1,
                })

        return self._dedup(all_candidates)

    # ------------------------------------------------ per-element generation

    def _candidates_for_element(self, el: Tag) -> List[Dict[str, Any]]:
        """Generate locator candidates for a single BeautifulSoup Tag."""
        tag = el.name
        attrs: dict[str, str] = {}
        for k, v in el.attrs.items():
            if isinstance(v, list):
                attrs[k] = " ".join(v)
            else:
                attrs[k] = str(v)

        candidates: list[dict] = []

        # 1) id-based
        el_id = attrs.get("id")
        if el_id:
            candidates.append({"type": "css", "value": f"#{el_id}", "score": 100})
            candidates.append({"type": "css", "value": f"{tag}#{el_id}", "score": 95})

        # 2) attribute-based css
        for a in self.IMPORTANT_ATTRS:
            val = attrs.get(a)
            if val and a != "id":
                candidates.append({"type": "css", "value": f'{tag}[{a}="{val}"]', "score": 80})
                candidates.append({"type": "css", "value": f'[{a}="{val}"]', "score": 75})

        # 3) class fallback
        cls = attrs.get("class")
        if cls:
            cls_list = cls.split()
            cls_list = [c for c in cls_list if c][:2]
            if cls_list:
                candidates.append({"type": "css", "value": tag + "".join([f".{c}" for c in cls_list]), "score": 60})

        # 4) xpath fallback
        xpath = self._build_basic_xpath(tag, attrs)
        candidates.append({"type": "xpath", "value": xpath, "score": 40})

        return candidates

    # ------------------------------------------------------------ utilities

    @staticmethod
    def _dedup(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Dedup and ensure RAW (strip outer quotes if someone supplied them)."""
        seen: set[tuple[str, str]] = set()
        out: list[dict] = []
        for c in sorted(candidates, key=lambda x: x["score"], reverse=True):
            v = c["value"].strip()
            if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                v = v[1:-1].strip()
            key = (c["type"], v)
            if key in seen:
                continue
            seen.add(key)
            out.append({**c, "value": v})
        return out

    def merge_external_candidate(self, candidates: List[Dict[str, Any]], element_candidate: dict) -> List[Dict[str, Any]]:
        """
        Merge an upstream element_candidate (from Element Locator Engine) into
        the generated candidates list.  The external candidate is treated as a
        high-quality hint: its score is capped at 90 so a local ID-based match
        (score 100) still wins, but it outranks attribute/class/xpath fallbacks.

        If element_candidate is None, empty, or missing required fields, the
        original candidates list is returned unchanged.
        """
        if not element_candidate or not isinstance(element_candidate, dict):
            return candidates

        # Determine the best available locator value from the external candidate
        ext_value = (
            element_candidate.get("css")
            or element_candidate.get("xpath")
            or element_candidate.get("full_xpath")
            or ""
        ).strip()

        if not ext_value:
            return candidates

        # Determine type
        if ext_value.startswith("//") or ext_value.startswith("("):
            ext_type = "xpath"
        else:
            ext_type = "css"

        # Score: use upstream score if valid (1-100 range), else default to 90
        raw_score = element_candidate.get("score")
        if isinstance(raw_score, (int, float)) and 1 <= raw_score <= 100:
            ext_score = min(int(raw_score), 90)  # cap at 90 so local id=100 wins
        else:
            ext_score = 90

        # Remove outer quotes if present (RAW invariant)
        if (ext_value.startswith("'") and ext_value.endswith("'")) or \
           (ext_value.startswith('"') and ext_value.endswith('"')):
            ext_value = ext_value[1:-1].strip()

        # Avoid duplicates — if same value already exists, boost its score instead
        for c in candidates:
            if c["value"] == ext_value:
                c["score"] = max(c["score"], ext_score)
                c["source"] = "external+internal"
                return candidates

        # Insert the external candidate
        candidates.append({
            "type": ext_type,
            "value": ext_value,
            "score": ext_score,
            "source": "external",
            "strategy": element_candidate.get("strategy", ""),
        })

        return candidates

    def pick_best(self, candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None
        return sorted(candidates, key=lambda x: x["score"], reverse=True)[0]

    def _build_basic_xpath(self, tag: str, attrs: dict) -> str:
        for k in ["id", "name", "aria-label", "placeholder", "title"]:
            v = attrs.get(k)
            if v:
                # XPath single-quoted value (escape single quotes if needed)
                safe = v.replace("'", "\\'")
                return f"//{tag}[@{k}='{safe}']"
        return f"//{tag}"
