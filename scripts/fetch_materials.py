#!/usr/bin/env python3
"""
Fetch study material and previous year question papers (PYQs) for any exam.

Sources are configured per exam profile (profiles/<exam>.json, "sources" key).
Pluggable adapters:

  * ignou-pyq-archive : IGNOU's official previous-question archive
                        (webservices.ignou.ac.in). Works for any programme:
                        set "archive_path" (e.g. "SOSS/XXXX") in the profile.
                        URLs are deterministic, no searching needed.
  * dspace-community  : any DSpace repository community/collection (e.g. an
                        eGyankosh community). Crawls sub-communities and item
                        pages and downloads every PDF bitstream it finds.
  * url-list          : a plain list of PDF URLs in the profile
                        ("url_list": [{"url": ..., "folder": ...}]) or a text
                        file of URLs via --url-file.

Stdlib only. Safe to re-run: existing files are skipped, failures are listed
at the end so you can retry. Examples:

    python scripts/fetch_materials.py --profile my-exam            # all sources in the profile
    python scripts/fetch_materials.py --profile my-exam --dry-run  # show what it would get
    python scripts/fetch_materials.py --url-file urls.txt          # one-off list of PDF URLs
"""

import argparse
import json
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
IGNOU_PYQ_PATTERN = ("https://webservices.ignou.ac.in/pre-question/"
                     "Question%20Paper%20{session}%20{year}/{archive_path}/{code}{ext}")
DEFAULT_CODE_RE = r"\b([A-Z]{2,6}-?\d{3,})\b"


def load_profile(arg):
    cand = Path(arg)
    if cand.exists():
        return json.loads(cand.read_text(encoding="utf-8"))
    prof_dir = REPO_ROOT / "profiles"
    for f in sorted(prof_dir.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if arg.lower() in (d.get("id", "").lower(), f.stem.lower(), d.get("name", "").lower()):
            return d
    raise SystemExit(f"Profile '{arg}' not found (looked in {prof_dir}). "
                     f"Create one with: python scripts/new_profile.py")


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
# Adapter: ignou-pyq-archive (deterministic PYQ URLs)
# ---------------------------------------------------------------------------

def fetch_pyq_archive(cfg, out_dir, timeout, dry_run):
    archive_path = cfg.get("archive_path")
    codes = cfg.get("codes", [])
    if not archive_path or not codes:
        print("  [!] pyq_archive adapter needs 'archive_path' and 'codes' in the profile.")
        return {"downloaded": [], "skipped": [], "missed": [], "failed": []}
    years = range(cfg.get("from_year", 2019), cfg.get("to_year", 2025) + 1)
    sessions = cfg.get("sessions", ["June", "December"])
    stats = {"downloaded": [], "skipped": [], "missed": [], "failed": []}
    for code in codes:
        for year in years:
            for session in sessions:
                got = False
                for ext in (".pdf", ".PDF"):
                    url = IGNOU_PYQ_PATTERN.format(session=session, year=year,
                                                   archive_path=archive_path, code=code, ext=ext)
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
                            got = True
                            break
                    except Exception as e:
                        stats["failed"].append((url, str(e)))
                        got = True
                        break
                if not got:
                    stats["missed"].append(f"{code} {session} {year}")
    return stats


# ---------------------------------------------------------------------------
# Adapter: dspace-community (crawl any DSpace community/collection for PDFs)
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


def fetch_dspace_community(cfg, out_dir, timeout, delay, max_files, dry_run):
    root = cfg.get("community")
    if not root:
        print("  [!] dspace-community adapter needs 'community' (URL) in the profile.")
        return {"downloaded": [], "skipped": [], "failed": [], "pages": 0}
    host = urlparse(root).netloc
    code_re = re.compile(cfg.get("code_regex", DEFAULT_CODE_RE))
    aliases = cfg.get("course_aliases", {})
    handle_re = re.compile(r"/handle/[^/]+/\d+")

    def code_from(text):
        m = code_re.search(text or "")
        if not m:
            return None
        return aliases.get(m.group(1), m.group(1))

    stats = {"downloaded": [], "skipped": [], "failed": [], "pages": 0}
    queue = [(root, None, 0)]  # (url, course context, depth)
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
            if urlparse(full).netloc != host:
                continue
            low = full.lower()
            if "/bitstream/" in low and ".pdf" in low:
                m = re.search(r"/([^/]+\.pdf)", full, re.IGNORECASE)
                fname = m.group(1) if m else "document.pdf"
                folder = ctx or "misc"
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
            elif handle_re.search(full):
                c = code_from(text)
                queue.append((full, c if c else ctx, depth + 1))
        time.sleep(delay)
    return stats


# ---------------------------------------------------------------------------
# Adapter: url-list
# ---------------------------------------------------------------------------

def fetch_url_list(items, out_dir, timeout, dry_run):
    stats = {"downloaded": [], "skipped": [], "failed": []}
    for item in items:
        url = item["url"] if isinstance(item, dict) else item
        folder = item.get("folder", "misc") if isinstance(item, dict) else "misc"
        name = item.get("name") if isinstance(item, dict) else None
        fname = name or re.search(r"/([^/]+\.pdf)", url, re.IGNORECASE)
        fname = fname if isinstance(fname, str) else (fname.group(1) if fname else "document.pdf")
        dest = out_dir / "extra" / folder / fname
        if dry_run:
            print(f"  would get: {url}")
            continue
        if dest.exists() and dest.stat().st_size > 0:
            stats["skipped"].append(str(dest))
            continue
        try:
            size = download_pdf(url, dest, timeout)
            stats["downloaded"].append(str(dest))
            print(f"  [ok] {fname} ({size // 1024} KB)")
        except Exception as e:
            stats["failed"].append((url, str(e)))
    return stats


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Download study material and PYQs for any exam profile.")
    ap.add_argument("--profile", help="Exam profile: id/name in profiles/ or a path")
    ap.add_argument("--url-file", help="Text file with one PDF URL per line (no profile needed)")
    ap.add_argument("--out", default=None, help="Output directory (default: materials/<profile-id>/)")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--delay", type=float, default=1.0, help="Seconds between crawl requests (be polite)")
    ap.add_argument("--max-files", type=int, default=250, help="Safety cap on crawled downloads per run")
    ap.add_argument("--dry-run", action="store_true", help="List what would be downloaded, get nothing")
    args = ap.parse_args()

    profile = None
    if args.profile:
        profile = load_profile(args.profile)
    elif not args.url_file:
        ap.error("give --profile <exam> or --url-file <urls.txt>")

    out_dir = Path(args.out) if args.out else REPO_ROOT / "materials" / (profile.get("id", "misc") if profile else "misc")
    print(f"Output: {out_dir}\n")
    sources = (profile or {}).get("sources", {})

    if profile and sources.get("pyq_archive"):
        print("== Previous Year Question Papers (pyq_archive adapter) ==")
        s = fetch_pyq_archive(sources["pyq_archive"], out_dir, args.timeout, args.dry_run)
        if not args.dry_run:
            print(f"PYQs: {len(s['downloaded'])} downloaded, {len(s['skipped'])} already had, "
                  f"{len(s['missed'])} not on server, {len(s['failed'])} failed\n")

    if profile and sources.get("slm_repository"):
        print("== Study Material (dspace-community adapter) ==")
        s = fetch_dspace_community(sources["slm_repository"], out_dir, args.timeout,
                                   args.delay, args.max_files, args.dry_run)
        print(f"SLM: {len(s['downloaded'])} downloaded, {len(s['skipped'])} already had, "
              f"{len(s['failed'])} failed, {s['pages']} pages crawled\n")

    items = list(sources.get("url_list", []))
    if args.url_file:
        items += [line.strip() for line in Path(args.url_file).read_text().splitlines()
                  if line.strip() and not line.startswith("#")]
    if items:
        print("== Extra URLs (url-list adapter) ==")
        s = fetch_url_list(items, out_dir, args.timeout, args.dry_run)
        if not args.dry_run:
            print(f"URLs: {len(s['downloaded'])} downloaded, {len(s['skipped'])} already had, {len(s['failed'])} failed\n")

    if not args.dry_run:
        print("Done. Re-run any time: existing files are skipped, failures can be retried.")


if __name__ == "__main__":
    main()
