from bs4 import BeautifulSoup


class LocatorGenerator:
    """
    Generates locator candidates from a single HTML element snippet.
    v1 Strategy (deterministic):
      - Prefer id-based CSS (#id)
      - Then tag#id
      - Then unique-ish attribute selectors (name, aria-label, placeholder, type)
      - Then class-based selector (tag.class1.class2) as fallback
      - Also generate a basic XPath as last resort
    """

    IMPORTANT_ATTRS = ["id", "name", "aria-label", "placeholder", "type", "role"]

    def generate_candidates(self, element_html: str) -> list[dict]:
        if not element_html or not element_html.strip():
            return []

        soup = BeautifulSoup(element_html, "html.parser")
        el = soup.find(True)  # first real tag
        if el is None or el.name is None:
            return []

        tag = el.name
        attrs = {k: (v if isinstance(v, str) else " ".join(v)) for k, v in el.attrs.items()}

        candidates = []

        # 1) id-based (best)
        el_id = attrs.get("id")
        if el_id:
            candidates.append({"type": "css", "value": f"#{el_id}", "score": 100})
            candidates.append({"type": "css", "value": f"{tag}#{el_id}", "score": 95})

        # 2) attribute-based CSS
        for a in self.IMPORTANT_ATTRS:
            val = attrs.get(a)
            if val and a != "id":
                # Escape double quotes for safe selector strings
                safe = str(val).replace('"', '\\"')
                candidates.append({"type": "css", "value": f"{tag}[{a}=\"{safe}\"]", "score": 80})
                candidates.append({"type": "css", "value": f"[{a}=\"{safe}\"]", "score": 75})

        # 3) class-based fallback
        cls = attrs.get("class")
        if cls:
            cls_list = cls.split() if isinstance(cls, str) else cls
            # Keep it short: first 2 classes
            cls_list = [c for c in cls_list if c][:2]
            if cls_list:
                candidates.append({"type": "css", "value": tag + "".join([f".{c}" for c in cls_list]), "score": 60})

        # 4) XPath fallback
        xpath = self._build_basic_xpath(tag, attrs)
        if xpath:
            candidates.append({"type": "xpath", "value": xpath, "score": 40})

        # Sort by score (desc) and deduplicate by (type,value)
        seen = set()
        out = []
        for c in sorted(candidates, key=lambda x: x["score"], reverse=True):
            key = (c["type"], c["value"])
            if key not in seen:
                seen.add(key)
                out.append(c)

        return out

    def pick_best(self, candidates: list[dict]) -> dict | None:
        if not candidates:
            return None
        return sorted(candidates, key=lambda x: x["score"], reverse=True)[0]

    def _build_basic_xpath(self, tag: str, attrs: dict) -> str | None:
        # Prefer id/name/placeholder in XPath
        for k in ["id", "name", "aria-label", "placeholder"]:
            v = attrs.get(k)
            if v:
                safe = str(v).replace("'", "\\'")
                return f"//{tag}[@{k}='{safe}']"
        return f"//{tag}"
