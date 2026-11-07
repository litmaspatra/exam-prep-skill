#!/usr/bin/env python3
"""
Fetch official, free IGNOU study material and previous year question papers.

Sources (both official IGNOU, free, no login, no card):
  * PYQs : webservices.ignou.ac.in pre-question archive.
           URLs are deterministic:
           .../pre-question/Question Paper <Session> <Year>/SOSS/CLIS/<CODE>.pdf
  * SLM  : eGyankosh (egyankosh.ac.in), the official IGNOU repository.
           CLIS community: https://egyankosh.ac.in/handle/123456789/34843
           The script crawls the community (course sub-communities -> blocks
           -> item pages) and downloads every PDF bitstream it finds.

Stdlib only. Safe to re-run: existing files are skipped, failures are listed
at the end so you can retry. Run from the repo root:

    python scripts/fetch_materials.py                 # everything
    python scripts/fetch_materials.py --pyqs          # question papers only
    python scripts/fetch_materials.py --slm           # study material only
    python scripts/fetch_materials.py --dry-run       # list what it would get
"""

import argparse
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (exam-prep-skill; personal educational use)"}

PYQ_PATTERN = ("https://webservices.ignou.ac.in/pre-question/"
               "Question%20Paper%20{session}%20{year}/SOSS/CLIS/{code}{ext}")
EGY_ROOT = "https://egyankosh.ac.in/handle/123456789/34843"
EGY_HOST = "egyankosh.ac.in"

DEFAULT_CODES = ["BLI-011", "BLII-012", "BLII-013", "BLII-014"]
# eGyankosh labels paper 1 "BLII-011"; the date sheet & PYQ archive use "BLI-011".
CODE_ALIASES = {"BLII-011": "BLI-011"}
CODE_RE = re.compile(r"\b(BLII?-?\d{3})\b", re.IGNORECASE)


def fetch_bytes(url, timeout):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download_pdf(url, dest, timeout):
    """Download url to dest, verifying it really is a PDF. Returns byte size."""
    data = fetch_bytes(url, timeout)
    if not data.startswith(b"%PDF"):
        raise ValueError("server returned a non-PDF page")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return len(data)


# ---------------------------------------------------------------------------
# Previous Year Question papers (deterministic URLs)
# ---------------------------------------------------------------------------

def fetch_pyqs(out_dir, codes, years, sessions, timeout, dry_run):
    stats = {"downloaded": [], "skipped": [], "missed": [], "failed": []}
    for code in codes:
        for year in years:
            for session in sessions:
                got = False
                for ext in (".pdf", ".PDF"):
                    url = PYQ_PATTERN.format(session=session, year=year, code=code, ext=ext)
                    dest = out_dir / "pyqs" / code / f"{code}_{session}_{year}.pdf"
                    if dry_run:
                        print(f"  would try: {url}")
                        got = True
                        break
                    if dest.exists() and dest.stat().st_size > 0:
                        stats["skipped"].append(str(dest))
                        got = True
                        break
                    try:
                        size = download_pdf(url, dest, timeout)
                        stats["downloaded"].append(str(dest))
                        print(f"  [ok] {code} {session} {year} ({size // 1024} KB)")
                        got = True
                        break
                    except urllib.error.HTTPError as e:
                        if e.code != 404:
                            stats["failed"].append((url, f"HTTP {e.code}"))
                            got = True  # don't also try the other extension
                            break
                    except Exception as e:
                        stats["failed"].append((url, str(e)))
                        got = True
                        break
                if not got:
                    stats["missed"].append(f"{code} {session} {year}")
    return stats


# ---------------------------------------------------------------------------
# eGyankosh study material (DSpace crawl)
# ---------------------------------------------------------------------------

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []  # (href, anchor text)
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            text = " ".join("".join(self._text).split())
            self.links.append((self._href, text))
            self._href = None


def course_from_text(text):
    m = CODE_RE.search(text or "")
    if not m:
        return None
    code = m.group(1).upper()
    if "-" not in code:  # normalise BLII012 -> BLII-012
        code = re.sub(r"^(BLII?)(\d)", r"\1-\2", code)
    return CODE_ALIASES.get(code, code)


def fetch_slm(out_dir, timeout, delay, max_files, dry_run):
    stats = {"downloaded": [], "skipped": [], "failed": [], "pages": 0}
    queue = [(EGY_ROOT, None, 0)]  # (url, course context, depth)
    visited = set()
    count = 0
    while queue:
        url, ctx, depth = queue.pop(0)
        if url in visited or depth > 6:
            continue
        visited.add(url)
        try:
            html = fetch_bytes(url, timeout).decode("utf-8", "replace")
        except Exception as e:
            stats["failed"].append((url, str(e)))
            continue
        stats["pages"] += 1
        parser = LinkParser()
        parser.feed(html)
        for href, text in parser.links:
            full = urljoin(url, href)
            if urlparse(full).netloc != EGY_HOST:
                continue
            low = full.lower()
            if "/bitstream/" in low and ".pdf" in low:
                m = re.search(r"/([^/]+\.pdf)", full, re.IGNORECASE)
                fname = m.group(1) if m else "document.pdf"
                folder = ctx or "Programme-Guide"
                dest = out_dir / "study_material" / folder / fname
                if dry_run:
                    print(f"  would get [{folder}] {fname}")
                    continue
                if dest.exists() and dest.stat().st_size > 0:
                    stats["skipped"].append(str(dest))
                    continue
                if count >= max_files:
                    print(f"  [!] --max-files {max_files} reached; rerun to continue.")
                    return stats
                try:
                    size = download_pdf(full, dest, timeout)
                    count += 1
                    stats["downloaded"].append(str(dest))
                    print(f"  [ok] [{folder}] {fname} ({size // 1024} KB)")
                    time.sleep(delay)
                except Exception as e:
                    stats["failed"].append((full, str(e)))
            elif "/handle/123456789/" in low:
                code = course_from_text(text)
                new_ctx = code if code else ctx
                queue.append((full, new_ctx, depth + 1))
        time.sleep(delay)
    return stats


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Download official free IGNOU CLIS study material and PYQs.")
    ap.add_argument("--pyqs", action="store_true", help="Fetch previous year question papers")
    ap.add_argument("--slm", action="store_true", help="Fetch eGyankosh study material")
    ap.add_argument("--out", default=str(REPO_ROOT / "materials"), help="Output directory")
    ap.add_argument("--codes", nargs="+", default=DEFAULT_CODES)
    ap.add_argument("--from-year", type=int, default=2019)
    ap.add_argument("--to-year", type=int, default=2025)
    ap.add_argument("--sessions", nargs="+", default=["June", "December"])
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--delay", type=float, default=1.0, help="Seconds between SLM requests (be polite)")
    ap.add_argument("--max-files", type=int, default=250, help="Safety cap on SLM downloads per run")
    ap.add_argument("--dry-run", action="store_true", help="List what would be downloaded, get nothing")
    args = ap.parse_args()

    if not (args.pyqs or args.slm):
        args.pyqs = args.slm = True

    out_dir = Path(args.out)
    years = list(range(args.from_year, args.to_year + 1))
    print(f"Output: {out_dir}\n")

    if args.pyqs:
        print("== Previous Year Question Papers (webservices.ignou.ac.in) ==")
        s = fetch_pyqs(out_dir, args.codes, years, args.sessions, args.timeout, args.dry_run)
        if not args.dry_run:
            print(f"PYQs: {len(s['downloaded'])} downloaded, {len(s['skipped'])} already had, "
                  f"{len(s['missed'])} not on server, {len(s['failed'])} failed")
            for item, err in s["failed"]:
                print(f"  failed: {item} ({err})")
            print()

    if args.slm:
        print("== Study Material / SLM (egyankosh.ac.in) ==")
        s = fetch_slm(out_dir, args.timeout, args.delay, args.max_files, args.dry_run)
        print(f"SLM: {len(s['downloaded'])} downloaded, {len(s['skipped'])} already had, "
              f"{len(s['failed'])} failed, {s['pages']} pages crawled")
        for item, err in s["failed"][:20]:
            print(f"  failed: {item} ({err})")
        print()

    if not args.dry_run:
        print("Done. Re-run any time: existing files are skipped, failures can be retried.")


if __name__ == "__main__":
    main()
