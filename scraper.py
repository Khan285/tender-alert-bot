#!/usr/bin/env python3
"""Find QA / IT consultant EOIs & tenders on BPPA/CPTU pages and alert via Telegram.

Usage:
  python scraper.py          # normal run (sends alerts for NEW matches only)
  python scraper.py --test   # send a Telegram test message
  python scraper.py --dry    # print matches, no Telegram, don't save state
"""
import json, os, re, sys, time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
STATE_FILE = ROOT / "seen.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (personal tender alert; once-daily)"}


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def collect_links():
    pat = re.compile(CONFIG["link_pattern"])
    links = {}
    for page in CONFIG["listing_urls"]:
        try:
            soup = BeautifulSoup(fetch(page), "html.parser")
        except Exception as e:
            print(f"[warn] listing failed {page}: {e}")
            continue
        for a in soup.find_all("a", href=True):
            if pat.search(a["href"]):
                links[urljoin(page, a["href"])] = a.get_text(" ", strip=True)
    return links


def parse_detail(html):
    soup = BeautifulSoup(html, "html.parser")
    lines = [l.strip() for l in soup.get_text("\n").split("\n") if l.strip()]
    title = ""
    for i, l in enumerate(lines):
        if "title of service" in l.lower():
            for nxt in lines[i + 1:i + 5]:
                if nxt not in (":", "|", "-"):
                    title = nxt.strip(" |:")
                    break
            break
    if not title and soup.title:
        title = soup.title.get_text(strip=True)

    def grab(label):
        for i, l in enumerate(lines):
            if label in l.lower():
                for nxt in lines[i + 1:i + 4]:
                    if nxt not in (":", "|", "-"):
                        return nxt.strip(" |:")
        return ""

    return {
        "title": title,
        "type": grab("expression of interest for selection of"),
        "deadline": grab("last date") or grab("deadline"),
        "text": " ".join(lines),
    }


def matches(text):
    low = text.lower()
    hit = [k for k in CONFIG["keywords_any_case"] if k in low]
    hit += [k for k in CONFIG["keywords_exact_case"]
            if re.search(rf"\b{re.escape(k)}\b", text)]
    return hit


def telegram(msg):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        sys.exit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
    for i in range(0, len(msg), 3800):
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": msg[i:i + 3800],
                  "disable_web_page_preview": True},
            timeout=30,
        )
        r.raise_for_status()


def main():
    if "--test" in sys.argv:
        telegram("✅ Tender alert bot is connected.")
        return
    dry = "--dry" in sys.argv

    seen = set(json.loads(STATE_FILE.read_text())) if STATE_FILE.exists() else set()
    links = collect_links()
    print(f"Found {len(links)} listing links, {len(seen)} already seen")
    if not links:
        print("[warn] No links found. Check listing_urls / link_pattern in config.json")

    new_urls = [u for u in links if u not in seen][: CONFIG["max_detail_pages_per_run"]]
    found = []
    for u in new_urls:
        try:
            d = parse_detail(fetch(u))
        except Exception as e:
            print(f"[warn] {u}: {e}")
            continue  # not marked seen, retry next run
        seen.add(u)
        hit = matches(d["title"] + " " + d["text"][:3000])
        if hit:
            found.append((u, d, hit))
        time.sleep(CONFIG["request_delay_seconds"])

    for u, d, hit in found:
        msg = (f"🔔 New match\n{d['title'] or 'Untitled'}\n"
               f"Type: {d['type'] or '-'}\nKeywords: {', '.join(sorted(set(hit))[:6])}\n{u}")
        print(msg, "\n")
        if not dry:
            telegram(msg)

    if not dry:
        STATE_FILE.write_text(json.dumps(sorted(seen), indent=0))
    print(f"Done. {len(found)} new matches.")


if __name__ == "__main__":
    main()
