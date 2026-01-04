import re
from bs4 import BeautifulSoup

MONTHS = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

def normalize_date(raw: str) -> str:
    """
    Convert messy suffix dates like:
    '– 20th December 2025' -> 'December 2025'
    'Commencing Soon (January 2026)' -> 'January 2026'
    'Registration Closed' -> 'Closed'
    '' -> 'N/A'
    """
    if not raw:
        return "N/A"

    t = re.sub(r"\s+", " ", raw).strip()

    if "Registration Closed" in t:
        return "Closed"

    # Parenthesis month/year: (January 2026)
    m = re.search(r"\((%s)\s+(\d{4})\)" % "|".join(MONTHS), t, re.IGNORECASE)
    if m:
        return f"{m.group(1).title()} {m.group(2)}"

    # Normal form: 20th December 2025 / 01st November 2025
    m = re.search(r"(\d{1,2})(st|nd|rd|th)?\s+(%s)\s+(\d{4})" % "|".join(MONTHS), t, re.IGNORECASE)
    if m:
        return f"{m.group(3).title()} {m.group(4)}"

    # Month Year anywhere
    m = re.search(r"(%s)\s+(\d{4})" % "|".join(MONTHS), t, re.IGNORECASE)
    if m:
        return f"{m.group(1).title()} {m.group(2)}"

    return t  # fallback (keeps something useful)

def split_name_and_date(text: str) -> tuple[str, str]:
    """
    Input examples:
    'Advanced Certificate Program in Artificial Intelligence – 20th December 2025'
    'Diploma in Business Management'
    """
    if not text:
        return "", "N/A"

    # remove weird double dashes spacing
    cleaned = " ".join(text.split()).strip()

    # Try split on dash/en-dash
    parts = re.split(r"\s+[–-]\s+", cleaned, maxsplit=1)
    if len(parts) == 2:
        name = parts[0].strip()
        date = normalize_date(parts[1].strip())
        return name, date

    # No date part
    return cleaned, "N/A"

def parse_programs_from_html(block_html: str) -> list[dict]:
    """
    Parses a tab section HTML and returns:
    [{ "Program Name": "...", "Starting Date": "..." , "URL": "..." }, ...]
    """
    soup = BeautifulSoup(block_html, "html.parser")
    results = []

    # The program links are anchors containing text in span.zn-buttonText
    links = soup.select("div.zn-buttonWrapper a[itemprop='url']")
    for a in links:
        url = a.get("href", "").strip()
        txt_el = a.select_one("span.zn-buttonText")
        txt = txt_el.get_text(" ", strip=True) if txt_el else a.get_text(" ", strip=True)

        name, date = split_name_and_date(txt)
        if name:
            results.append({
                "Program Name": name,
                "Starting Date": date,
                "URL": url
            })

    # Deduplicate by (name,url)
    seen = set()
    uniq = []
    for r in results:
        key = (r["Program Name"], r["URL"])
        if key not in seen:
            uniq.append(r)
            seen.add(key)

    return uniq
