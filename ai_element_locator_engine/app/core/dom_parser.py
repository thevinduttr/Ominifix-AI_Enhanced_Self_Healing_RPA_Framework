"""
app.core.dom_parser

Utility functions for parsing HTML into a DomSnapshot and extracting commonly
used attributes. This module encapsulates lxml/HTML parsing so other parts of
the system do not depend directly on a specific parsing library.
"""

from __future__ import annotations

from typing import Optional

from lxml import html, etree

from app.core.models.internal import DomSnapshot


def parse_html(page_html: str, page_url: str, page_name: Optional[str] = None) -> DomSnapshot:
    """
    Parse raw HTML into a DomSnapshot (lxml root + metadata).

    Primary representation used by strategies is lxml HtmlElement tree.
    """
    root: html.HtmlElement = html.fromstring(page_html)
    return DomSnapshot(root=root, page_url=page_url, page_name=page_name)


def get_visible_text(node: etree._Element) -> str:
    """
    Get the concatenated visible text for a node.
    """
    text = " ".join(node.itertext())
    return " ".join(text.split())  # normalize whitespace


def build_simple_css_selector(node: etree._Element) -> str:
    """
    Build a best-effort CSS selector from a node.

    Priority:
    1) id -> tag#id
    2) first class -> tag.class
    3) name attr -> tag[name="..."]
    4) type attr -> tag[type="..."]
    5) tag only

    Notes:
    - This does not guarantee uniqueness, but works well for demo and reporting.
    - lxml sometimes returns class as string; keep parsing defensive.
    """
    # Normalize tag name and strip namespace if present
    tag = getattr(node, "tag", None) or "element"
    if isinstance(tag, str) and "}" in tag:
        tag = tag.split("}", 1)[1]
    tag = str(tag).lower()

    node_id = node.get("id")
    if node_id:
        return f"{tag}#{node_id}"
    
    class_attr = node.get("class")
    if class_attr:
        # lxml gives class as string, but be defensive
        if isinstance(class_attr, (list, tuple)):
            classes = [c for c in class_attr if c]
        else:
            classes = [c for c in str(class_attr).split() if c]

        if classes:
            return f"{tag}.{classes[0]}"
    
    name_attr = node.get("name")
    if name_attr:
        return f'{tag}[name="{name_attr}"]'
    
    type_attr = node.get("type")
    if type_attr:
        return f'{tag}[type="{type_attr}"]'

    return tag
