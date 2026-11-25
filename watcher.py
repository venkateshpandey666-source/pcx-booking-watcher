import os
import re
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
STATE_PATH = ROOT / "state.json"
SCREEN_KEYWORD = CONFIG.get("screen_keyword", "PCX Screen")

def telegram(message: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("Telegram not configured; message will only appear in workflow logs.")
        print(message)
        return
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
        timeout=20,
    )
    response.raise_for_status()

def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")

def normalize(text):
    return re.sub(r"\s+", " ", text or "").strip()

def digest(text):
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

def extract_page(page, url, name, kind):
    result = {
        "name": name, "url": url, "kind": kind,
        "title": "", "text": "", "pcx_found": False,
        "seat_available_count": None, "seat_sold_count": None,
        "status": "unknown", "error": None
    }
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except PlaywrightTimeoutError:
            pass
        page.wait_for_timeout(4000)
        result["title"] = normalize(page.title())
        body_text = normalize(page.locator("body").inner_text(timeout=15000))
        result["text"] = body_text[:12000]
        result["pcx_found"] = bool(re.search(r"\bPCX\b", body_text, re.I))

        # Best-effort seat parsing. BookMyShow may change its DOM or render
        # seats as canvas/SVG; in that case we deliberately report unknown.
        seat_nodes = page.locator(
            "[aria-label], [title], [data-testid], [class*='seat'], [class*='Seat']"
        )
        samples = []
        try:
            count = min(seat_nodes.count(), 1500)
            for i in range(count):
                node = seat_nodes.nth(i)
                bits = []
                for attr in ("aria-label", "title", "data-testid", "class"):
                    val = node.get_attribute(attr)
                    if val:
                        bits.append(val)
                if bits:
                    samples.append(" ".join(bits))
        except Exception:
            pass
        seat_blob = " ".join(samples).lower()
        available_tokens = ("available", "seat-available", "seat_available", "vacant")
        sold_tokens = ("sold", "unavailable", "booked", "seat-sold", "seat_sold")
        avail = sum(1 for s in samples if any(t in s.lower() for t in available_tokens))
        sold = sum(1 for s in samples if any(t in s.lower() for t in sold_tokens))
        if avail or sold:
            result["seat_available_count"] = avail
            result["seat_sold_count"] = sold
            result["status"] = "seat data detected"
        elif kind == "booking":
            if re.search(r"PCX\s*Screen", body_text, re.I):
                result["status"] = "PCX listing visible"
            else:
                result["status"] = "PCX not confirmed on page"
        else:
            result["status"] = "seat layout loaded; seat count not readable"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["status"] = "page error"
    return result

def main():
    state = load_state()
    current = {}
    reports = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
        )
        page = context.new_page()
        page.set_default_timeout(15000)

        for item in CONFIG.get("booking_pages", []):
            reports.append(extract_page(page, item["url"], item["name"], "booking"))
        for item in CONFIG.get("seat_pages", []):
            reports.append(extract_page(page, item["url"], item["name"], "seat"))

        browser.close()

    now = datetime.now(timezone.utc).astimezone().strftime("%d %b %Y, %I:%M:%S %p %Z")
    alerts = []
    for report in reports:
        key = digest(report["url"])
        signature = digest(json.dumps({
            "title": report["title"],
            "text": report["text"],
            "status": report["status"],
            "available": report["seat_available_count"],
            "sold": report["seat_sold_count"],
            "error": report["error"]
        }, sort_keys=True))
        previous = state.get(key)
        current[key] = signature

        # Alert on first successful observation and any subsequent page change.
        # This is a change detector, not proof that a show has newly opened.
        if previous != signature:
            snippet = report["text"][:500] if report["text"] else report["error"] or "No readable page text"
            alerts.append(
                f"🎬 {CONFIG.get('movie')} — {report['name']}\n"
                f"Status: {report['status']}\n"
                f"PCX keyword visible: {'YES' if report['pcx_found'] else 'NO / not readable'}\n"
                f"Available seats (best effort): {report['seat_available_count']}\n"
                f"Sold seats (best effort): {report['seat_sold_count']}\n"
                f"Checked: {now}\n"
                f"{report['url']}\n\n"
                f"Page excerpt: {snippet}"
            )

    # Keep state even when a page is unchanged. The GitHub workflow commits it.
    state.update(current)
    save_state(state)

    if alerts:
        for alert in alerts:
            telegram(alert)
    else:
        print(f"No page changes detected at {now}.")

    for report in reports:
        print(json.dumps({k: v for k, v in report.items() if k != "text"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
    telegram("✅ PCX Booking Watcher: Telegram test successful!")
