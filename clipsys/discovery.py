"""Finds campaigns on listing pages you configure, reads their terms, extracts rules.

Only point CAMPAIGN_LIST_URLS at sites whose terms allow automated reading.
"""
import urllib.robotparser
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .db import conn, dumps
from .config import CAMPAIGN_LIST_URLS
from .rules import extract_rules, campaign_usable

HEADERS = {"User-Agent": "clip-pipeline/1.0 (personal research tool)"}


def _allowed(url: str) -> bool:
    p = urlparse(url)
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{p.scheme}://{p.netloc}/robots.txt")
    try:
        rp.read()
    except Exception:
        return False
    return rp.can_fetch(HEADERS["User-Agent"], url)


def _page_text(url: str) -> tuple[str, str, list[str]]:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    title = (soup.title.string or url).strip() if soup.title else url
    links = [urljoin(url, a["href"]) for a in soup.find_all("a", href=True)]
    return title, soup.get_text("\n", strip=True), links


def discover() -> int:
    """Crawl listing pages, store campaign pages, extract rules. Returns count of usable campaigns."""
    usable = 0
    with conn() as c:
        for list_url in CAMPAIGN_LIST_URLS:
            if not _allowed(list_url):
                print(f"[skip] robots.txt disallows {list_url}")
                continue
            _, _, links = _page_text(list_url)
            host = urlparse(list_url).netloc
            campaign_links = {l.split("#")[0] for l in links if urlparse(l).netloc == host}
            for url in sorted(campaign_links)[:50]:
                if c.execute("SELECT 1 FROM campaigns WHERE url=?", (url,)).fetchone():
                    continue
                if not _allowed(url):
                    continue
                try:
                    title, text, _ = _page_text(url)
                    rules = extract_rules(text)
                except Exception as e:
                    print(f"[err] {url}: {e}")
                    continue
                ok, why = campaign_usable(rules)
                status = "rules_ok" if ok else "blocked"
                c.execute(
                    "INSERT INTO campaigns(url,title,terms_text,rules_json,status) VALUES(?,?,?,?,?)",
                    (url, title, text[:50000], dumps(rules), status),
                )
                if ok:
                    usable += 1
                    for src in rules["allowed_source_urls"]:
                        c.execute(
                            "INSERT OR IGNORE INTO sources(campaign_id,url) VALUES((SELECT id FROM campaigns WHERE url=?),?)",
                            (url, src),
                        )
                print(f"[{status}] {title[:60]} ({why})")
    return usable
