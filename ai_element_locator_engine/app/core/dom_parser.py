"""
app.core.dom_parser

Utility functions for parsing HTML into a DomSnapshot and extracting commonly
used attributes. This module encapsulates lxml/HTML parsing so other parts of
the system do not depend directly on a specific parsing library.
"""

from __future__ import annotations

from typing import Optional

from bs4 import BeautifulSoup
from lxml import html, etree

from app.core.models.internal import DomSnapshot


def parse_html(page_html: str, page_url: str, page_name: Optional[str] = None) -> DomSnapshot:
    """
    Parse raw HTML into a DomSnapshot (lxml root + metadata).

    We also create a BeautifulSoup object when needed, but the primary
    representation the strategies will use is lxml's HtmlElement tree.
    """
    root: html.HtmlElement = html.fromstring(page_html)
    return DomSnapshot(root=root, page_url=page_url, page_name=page_name)


def get_visible_text(node: etree._Element) -> str:
    """
    Get the concatenated visible text for a node. For now this is a simple
    join of all text nodes under the element.
    """
    text = " ".join(node.itertext())
    return " ".join(text.split())  # normalise whitespace


def build_simple_css_selector(node: etree._Element) -> str:
    """
    Build a simple CSS selector from a node by using id > classes > tag name.
    This does not guarantee uniqueness but works well in many practical cases.
    """
    tag = node.tag
    node_id = node.get("id")
    class_attr = node.get("class")

    if node_id:
        return f"{tag}#{node_id}"

    if class_attr:
        # take first class only for simplicity
        first_class = class_attr.split()[0]
        return f"{tag}.{first_class}"

    return tag
