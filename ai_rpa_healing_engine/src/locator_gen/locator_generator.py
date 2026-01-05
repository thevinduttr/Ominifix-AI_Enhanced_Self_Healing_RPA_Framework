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
