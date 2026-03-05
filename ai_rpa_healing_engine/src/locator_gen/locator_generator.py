from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup


class LocatorGenerator:
    """
    Generates RAW locator candidates from a single HTML element snippet.
    IMPORTANT:
      - Candidates returned here MUST be RAW selectors (NO wrapping quotes).
      - Quoting for Python code is handled later by the patcher.
    """

    IMPORTANT_ATTRS = ["id", "name", "aria-label", "placeholder", "type", "role", "title"]

    def generate_candidates(self, element_html: str) -> List[Dict[str, Any]]:
        if not element_html or not element_html.strip():
            return []

        # Parse fragment safely (avoid lxml wrapping into <html>)
        soup = BeautifulSoup(element_html, "html.parser")
        el = soup.find(True)  # first real tag
        if not el or not el.name:
            return []

        tag = el.name
        attrs = {}
        for k, v in el.attrs.items():
            if isinstance(v, list):
                attrs[k] = " ".join(v)
            else:
                attrs[k] = str(v)

        candidates = []

        # 1) id-based
        el_id = attrs.get("id")
        if el_id:
            candidates.append({"type": "css", "value": f"#{el_id}", "score": 100})
            candidates.append({"type": "css", "value": f"{tag}#{el_id}", "score": 95})

        # 2) attribute-based css
        for a in self.IMPORTANT_ATTRS:
            val = attrs.get(a)
            if val and a != "id":
                # Keep RAW selector (double-quotes inside selector are fine; patcher will wrap safely in single quotes)
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

        # Dedup and ensure RAW (strip outer quotes if someone supplied them)
        seen = set()
        out = []
        for c in sorted(candidates, key=lambda x: x["score"], reverse=True):
            v = c["value"].strip()

            # Remove outer quotes if present (RAW invariant)
            if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                v = v[1:-1].strip()

            key = (c["type"], v)
            if key in seen:
                continue
            seen.add(key)
            out.append({"type": c["type"], "value": v, "score": c["score"]})

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
