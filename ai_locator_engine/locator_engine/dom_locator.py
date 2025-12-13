from typing import List, Dict
from .dom_parser import parse_html_file, build_dom_tree_with_paths


def extract_dom_candidates(html_path: str,
                           element_role: str,
                           expected_text: str = None) -> List[Dict]:
    """
    Extract possible interactive elements: buttons, inputs[type=submit/button], links.
    Each candidate gets: tag, text, attrs, long_xpath.
    """
    soup = parse_html_file(html_path)
    dom_nodes = build_dom_tree_with_paths(soup)

    candidates = []

    interactive_tags = {"button", "a", "input"}

    for el, xpath in dom_nodes:
        if el.name not in interactive_tags:
            continue

        # filter inputs to actionable types
        if el.name == "input" and el.get("type") not in (None, "submit", "button"):
            continue

        text = (el.get_text() or "").strip()
        attrs = el.attrs
        tag = el.name
        el_id = attrs.get("id")
        cls = " ".join(attrs.get("class", []))
        input_type = attrs.get("type")

        # candidate "action" score rough rule (for now threshold in ML)
        rough_role = "unknown"
        if tag == "button" or input_type in ("submit", "button"):
            rough_role = "primary_action"
        elif tag == "a":
            rough_role = "link_action"

        candidates.append({
            "tag": tag,
            "text": text,
            "id": el_id,
            "class": cls,
            "type": input_type,
            "long_xpath": xpath,
            "rough_role": rough_role
        })

    return candidates
