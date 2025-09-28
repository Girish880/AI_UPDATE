import os
from datetime import datetime
from playwright.sync_api import sync_playwright


def ensure_dir(path: str):
    """Ensure a directory exists."""
    os.makedirs(path, exist_ok=True)


def safe_filename(name: str) -> str:
    """Make a test name safe for use in file paths."""
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)


def capture_artifacts(url: str, run_id: str, test_name: str) -> dict:
    """
    Capture artifacts (screenshot, DOM snapshot, console logs) for a test run.
    
    Args:
        url (str): Target URL (game/test environment).
        run_id (str): Unique run identifier.
        test_name (str): Name of the test case.

    Returns:
        dict: Paths to saved artifacts or error info.
    """
    artifacts = {}
    base_dir = os.path.join("reports", "artifacts", run_id)
    ensure_dir(base_dir)

    # Ensure test_name is safe for file paths
    safe_name = safe_filename(test_name)
    prefix = os.path.join(base_dir, safe_name)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        logs = []
        page.on("console", lambda msg: logs.append(msg.text))

        try:
            page.goto(url, timeout=15000)

            # Screenshot
            screenshot_path = f"{prefix}_screenshot.png"
            page.screenshot(path=screenshot_path)
            artifacts["screenshot"] = screenshot_path

            # DOM Snapshot
            dom_path = f"{prefix}_dom.html"
            with open(dom_path, "w", encoding="utf-8") as f:
                f.write(page.content())
            artifacts["dom_snapshot"] = dom_path

            # Console Logs
            log_path = f"{prefix}_logs.txt"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(logs))
            artifacts["logs"] = log_path

        except Exception as e:
            artifacts["error"] = str(e)

        finally:
            browser.close()

    return artifacts
