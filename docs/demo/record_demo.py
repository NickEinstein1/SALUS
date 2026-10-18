"""Record a ~2 minute SALUS UI demo for Graph Hacks submission."""

from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "raw"
API_KEY = "salus-dev-change-me"
BASE = "http://127.0.0.1:8080"
QUESTION = "Wing B lost cooling — what breaks and who do we page?"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*"):
        old.unlink()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(OUT),
            record_video_size={"width": 1440, "height": 900},
        )
        page = context.new_page()
        page.goto(BASE, wait_until="networkidle")
        time.sleep(2.5)

        # API key
        page.fill("#apiKeyInput", API_KEY)
        page.dispatch_event("#apiKeyInput", "change")
        time.sleep(1.5)

        # Show tracks
        page.hover("#track01")
        time.sleep(1)
        page.hover("#track02")
        time.sleep(1)
        page.hover("#track03")
        time.sleep(1.5)

        # Ask question
        page.fill("#question", QUESTION)
        time.sleep(1.2)
        page.click("#askBtn")

        # Wait for result / chat ready (investigation can take a bit)
        try:
            page.wait_for_selector(".chat-panel.is-ready", timeout=90000)
        except Exception:
            page.wait_for_timeout(25000)

        time.sleep(3)

        # Scroll context / path
        page.evaluate("window.scrollTo(0, 200)")
        time.sleep(2)
        page.click("#pathFindBtn")
        time.sleep(4)

        # Scroll chat into view emphasis
        page.locator("#chatPanel").scroll_into_view_if_needed()
        time.sleep(3)
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(2)

        # Linger so total video ~ narration length
        page.wait_for_timeout(25000)

        page.close()
        context.close()
        browser.close()

    videos = list(OUT.glob("*.webm"))
    if not videos:
        raise SystemExit("No video recorded")
    dest = ROOT / "screen.webm"
    videos[0].replace(dest)
    print(dest)


if __name__ == "__main__":
    main()
