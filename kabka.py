#!/usr/bin/env python3
"""
Interactive kabyle and georgian collision scanner + special report for Occitan & Kabyle.
New switch:
  --report    run all 4 combinations (site × device) and print a short
              summary that highlights collisions vs. ok/alt for oci & kab.
"""

import argparse
import re
import sys
import requests
from langcodes import Language
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

# --------------------------------------------------------------------------- #
CODES = {
    "oci": "Occitan",
    "kab": "Kabyle",
    "kam": "Kamba",
    "kac": "Kachin",
    "kal": "Greenlandic",
    "kar": "Karen",
    "kat": "Georgian",
    "kau": "Kanuri",
    "kaw": "Kawi",
    "kaz": "Kazakh",
}
SITES = {
    "1": ("DuckDuckGo", "https://duckduckgo.com/q=test "),
    "2": ("Nextcloud", "https://demo2.nextcloud.com/index.php/login "),
}
DEVICES = {
    "1": ("desktop", ""),
    "2": ("mobile", "Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/109.0 Firefox/119.0"),
}

# ------------------------------ data-driven rules -------------------------- #
ALT_MAPPINGS = {
    "oci": {"oc"},
    # kab variants handled below with startswith
}
FALLBACKS = {"en"}
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=None)
def _validated_lang(tag: str) -> Optional[Language]:
    try:
        lang = Language.get(tag)
        return lang if lang.is_valid() else None
    except Exception:
        return None

def locale_used(html: str, cookie: str) -> Optional[str]:
    if m := re.search(r'<html[^>]*\blang=["\']([-a-zA-Z]+)', html):
        return m.group(1)
    if m := re.search(r'ae=l=([-a-zA-Z]+)', cookie or ""):
        return m.group(1)
    return None

# --------------------------------------------------------------------------- #
def test_one(sess: requests.Session, url: str, ua: str, loose: bool) -> Dict[str, Tuple[str, str]]:
    """Return dict  code -> (label, returned_tag)  for one URL+UA."""
    results: Dict[str, Tuple[str, str]] = {}
    for code, name in CODES.items():
        headers = {"Accept-Language": code}
        if ua:
            headers["User-Agent"] = ua
        try:
            r = sess.get(url, headers=headers, timeout=15)
        except requests.RequestException as e:
            results[code] = ("error", str(e))
            continue

        got = locale_used(r.text, r.headers.get("Set-Cookie", ""))
        if not got:
            results[code] = ("unk", "no locale hint")
            continue
        if _validated_lang(got) is None:
            results[code] = ("unk", f"invalid locale {got!r}")
            continue

        # ----- alternates / fall-backs ----- #
        if code == "oci" and got == "oc":               # Occitan → oc
            results[code] = ("alt", got)
            continue
        if code == "kab" and got.startswith("kab"):     # any kab-*
            results[code] = ("alt", got)
            continue
        if code in ("oci", "kab") and any(got.startswith(f) for f in FALLBACKS):
            results[code] = ("fallback", got)
            continue

        # normal verdict
        if loose:
            label = "ok" if got.startswith(code) else "collision"
        else:
            label = "ok" if got == code else "collision"
        results[code] = (label, got)
    return results

# --------------------------------------------------------------------------- #
def choose_site() -> Tuple[str, str]:
    print("\nChoose site to test:")
    for k, (name, _) in SITES.items():
        print(f"  {k}  {name}")
    while True:
        choice = input("Enter 1 or 2: ").strip()
        if choice in SITES:
            return SITES[choice]
        print("Please type 1 or 2.")

def choose_device() -> Tuple[str, str]:
    print("\nChoose device profile:")
    for k, (name, _) in DEVICES.items():
        print(f"  {k}  {name}")
    while True:
        choice = input("Enter 1 or 2: ").strip()
        if choice in DEVICES:
            return DEVICES[choice]
        print("Please type 1 or 2.")

# --------------------------------------------------------------------------- #
def interactive_mode(loose: bool) -> None:
    site_name, site_url = choose_site()
    device_name, ua = choose_device()
    print(f"\nTesting {site_url}  ({device_name}) …\n")
    sess = requests.Session()
    results = test_one(sess, site_url, ua, loose)
    for code, name in CODES.items():
        label, got = results[code]
        print(f"{label}  {code}  {name}  →  {got}")

# --------------------------------------------------------------------------- #
def _job(sk: str, dk: str, loose: bool) -> Tuple[str, str, str, str, Dict[str, Tuple[str, str]]]:
    site_n, site_u = SITES[sk]
    dev_n, ua = DEVICES[dk]
    sess = requests.Session()
    return (sk, dk, site_n, dev_n, test_one(sess, site_u, ua, loose))

def report_mode(loose: bool) -> None:
    """Run all 4 combos and produce a focused report for oci & kab."""
    print("Generating Occitan & Kabyle report …\n")
    combos = (("1", "1"), ("1", "2"), ("2", "1"), ("2", "2"))
    report: Dict[Tuple[str, str, str], Tuple[str, str]] = {}

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_job, sk, dk, loose) for sk, dk in combos]
        for fut in as_completed(futures):
            sk, dk, site_n, dev_n, res = fut.result()
            print(f"Done  {site_n}  +  {dev_n}")
            for code in ("oci", "kab"):
                report[(site_n, dev_n, code)] = res[code]

    # ---- print summary ---- #
    print("\n" + "=" * 60)
    print("Occitan & Kabyle summary")
    print("=" * 60)
    for (site, dev, code), (label, got) in report.items():
        name = CODES[code]
        print(f"{site:10} | {dev:7} | {code:3} ({name:12}) → {got:12}  [{label}]")
    print("=" * 60)

    # ---- quick highlight ---- #
    collisions = [(s, d, c) for (s, d, c), (l, _) in report.items() if l == "collision"]
    if collisions:
        print("\nCollisions detected:")
        for s, d, c in collisions:
            print(f"  - {s} {d}  {c}")
    else:
        print("\nNo collisions for Occitan or Kabyle in this run.")

# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive ka*/kab scanner + report")
    parser.add_argument("--loose", action="store_true", help="accept language variants")
    parser.add_argument("--report", action="store_true", help="run full Occitan & Kabyle report")
    args = parser.parse_args()

    if args.report:
        report_mode(args.loose)
    else:
        interactive_mode(args.loose)

if __name__ == "__main__":
    main()
