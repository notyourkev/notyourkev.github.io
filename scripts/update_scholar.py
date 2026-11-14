#!/usr/bin/env python3
"""Refresh a public Google Scholar snapshot without third-party dependencies.

Unavailable pages never replace a successful snapshot. Use --self-test for
offline parser checks. No API key, browser login, or third-party API is needed.
"""

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen


PROFILE_ID = "dPrvOpQAAAAJ"
PROFILE_URL = f"https://scholar.google.com/citations?user={PROFILE_ID}&hl=zh-CN"
FETCH_URL = "https://scholar.google.com/citations?" + urlencode(
    {"user": PROFILE_ID, "hl": "en", "cstart": 0, "pagesize": 100}
)
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "scholar.json"
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Node:
    def __init__(self, tag="", attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    @property
    def text(self):
        return " ".join("".join(child if isinstance(child, str) else child.text for child in self.children).split())

    def find_all(self, *, tag=None, node_id=None, css_class=None):
        matches = []
        for child in self.children:
            if isinstance(child, str):
                continue
            if ((tag is None or child.tag == tag)
                and (node_id is None or child.attrs.get("id") == node_id)
                and (css_class is None or css_class in child.attrs.get("class", "").split())):
                matches.append(child)
            matches.extend(child.find_all(tag=tag, node_id=node_id, css_class=css_class))
        return matches


class ScholarHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def citation_number(text):
    value = re.sub(r"[,\s\u202f\u00a0]", "", text)
    return int(value) if re.fullmatch(r"[0-9]+", value) else None


def paper_url(href):
    """Only retain citation detail links belonging to this Scholar profile."""
    candidate = urljoin("https://scholar.google.com/", href)
    parsed = urlparse(candidate)
    query = parse_qs(parsed.query)
    citation_id = query.get("citation_for_view", [""])[0]
    if (parsed.scheme == "https" and parsed.netloc == "scholar.google.com"
        and parsed.path == "/citations" and query.get("view_op") == ["view_citation"]
        and citation_id.startswith(PROFILE_ID + ":")):
        return candidate
    return PROFILE_URL


def parse_profile(html):
    parser = ScholarHTML()
    parser.feed(html)
    root = parser.root
    names = root.find_all(node_id="gsc_prf_in")
    tables = root.find_all(node_id="gsc_rsb_st")
    if not names or not names[0].text or not tables:
        raise ValueError("Scholar profile or citation statistics missing (possibly a consent or blocked page)")
    total = None
    for row in tables[0].find_all(tag="tr"):
        labels = row.find_all(css_class="gsc_rsb_sc1")
        values = row.find_all(css_class="gsc_rsb_std")
        if labels and labels[0].text.casefold() in {"citations", "引用次数", "引用"} and values:
            total = citation_number(values[0].text)
            break
    if total is None:
        raise ValueError("A numeric all-time citation count could not be read")
    papers = []
    for row in root.find_all(css_class="gsc_a_tr"):
        titles = row.find_all(css_class="gsc_a_at")
        counts = row.find_all(css_class="gsc_a_ac")
        if not titles or not titles[0].text:
            continue
        papers.append({
            "title": titles[0].text,
            # Empty/changed cells remain unknown rather than an invented zero.
            "citations": citation_number(counts[0].text) if counts else None,
            "scholar_url": paper_url(titles[0].attrs.get("href", "")),
        })
    if not papers:
        raise ValueError("Publication rows missing; refusing a partial snapshot")
    return {
        "profile_url": PROFILE_URL,
        "status": "ok",
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "total_citations": total,
        "papers": papers,
    }


def fetch_profile():
    request = Request(FETCH_URL, headers={
        "User-Agent": "Mozilla/5.0 (compatible; AcademicHomepage/1.0)",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urlopen(request, timeout=25) as response:
        if urlparse(response.url).netloc != "scholar.google.com":
            raise ValueError("Scholar redirected outside the public profile host")
        raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError("Profile response exceeds the expected size")
        return raw.decode(response.headers.get_content_charset() or "utf-8")


def self_test():
    fixture = f"""<!doctype html><html><head><meta charset='utf-8'></head><body>
      <div id='gsc_prf_in'>Songyu Xu</div>
      <table id='gsc_rsb_st'><tr><th></th><th>All</th><th>Since 2021</th></tr>
      <tr><td class='gsc_rsb_sc1'><a>Citations</a></td><td class='gsc_rsb_std'>1,234</td><td class='gsc_rsb_std'>999</td></tr>
      <tr><td class='gsc_rsb_sc1'>h-index</td><td class='gsc_rsb_std'>8</td></tr></table>
      <table><tbody><tr class='gsc_a_tr'><td><a class='gsc_a_at' href='/citations?view_op=view_citation&amp;citation_for_view={PROFILE_ID}:abc'>A &amp; B: <b>Visual</b> Evaluation</a></td><td><a class='gsc_a_ac gs_ibl'>1,002</a></td></tr>
      <tr class='gsc_a_tr'><td><a class='gsc_a_at' href='https://example.com/'>Unknown count</a></td><td><a class='gsc_a_ac'></a></td></tr></tbody></table></body></html>"""
    parsed = parse_profile(fixture)
    assert parsed["total_citations"] == 1234
    assert parsed["papers"][0]["title"] == "A & B: Visual Evaluation"
    assert parsed["papers"][0]["citations"] == 1002
    assert parsed["papers"][1]["citations"] is None
    assert parsed["papers"][1]["scholar_url"] == PROFILE_URL
    assert f"citation_for_view={PROFILE_ID}:abc" in parsed["papers"][0]["scholar_url"]
    assert citation_number("1\u202f234") == 1234
    assert citation_number("-") is None
    for broken in ["<html>Verify you are human</html>", fixture.replace("1,234", "unavailable"), fixture.replace("gsc_a_tr", "changed-row")]:
        try:
            parse_profile(broken)
        except ValueError:
            continue
        raise AssertionError("An incomplete/blocked profile was accepted")
    print("Scholar parser checks passed (totals, article counts, entities, unknown cells, blocked pages)")


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--self-test", action="store_true")
    options = args.parse_args()
    if options.self_test:
        self_test()
        return
    try:
        snapshot = parse_profile(fetch_profile())
    except Exception as error:
        # Preserve the last successful snapshot, including its date and counts.
        print(f"Scholar sync unavailable; existing snapshot preserved: {error}", file=sys.stderr)
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)
    print(f"Updated {len(snapshot['papers'])} articles; all-time citations: {snapshot['total_citations']}")


if __name__ == "__main__":
    main()
