from bs4 import BeautifulSoup

def parse_html_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "lxml")
    return soup


def build_dom_tree_with_paths(soup):
    """
    Traverse DOM and attach an absolute XPath-like path to each element.
    Returns a list of (element, xpath).
    """
    results = []

    def traverse(node, path):
        # only element nodes
        if not hasattr(node, "name"):
            return
        if node.name is None:
            return

        same_tag_siblings = [c for c in node.parent.children
                             if hasattr(c, "name") and c.name == node.name] if node.parent else []
        if node.parent:
            index = same_tag_siblings.index(node) + 1 if len(same_tag_siblings) > 1 else 1
        else:
            index = 1

        if node.parent is None:
            current_path = f"/{node.name}[1]"
        else:
            current_path = f"{path}/{node.name}[{index}]"

        results.append((node, current_path))

        for child in node.children:
            traverse(child, current_path)

    # start from <html>
    html_tag = soup.html
    if html_tag:
        traverse(html_tag, "")

    return results
