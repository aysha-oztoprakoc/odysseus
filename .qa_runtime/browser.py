from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:7134"
evidence: dict[str, object] = {"viewports": [], "enabled": {}}

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    for width in (375, 768, 1280):
        page = browser.new_page(viewport={"width": width, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(BASE, wait_until="domcontentloaded")
        page.locator("#app-loader").evaluate("element => element.remove()")
        assert page.locator("#rail-files").count() == 0
        assert page.locator("#files-modal").count() == 0
        assert "Secrets Vault" not in page.locator("body").inner_text()
        screenshot = ROOT / f"files-disabled-{width}.png"
        page.screenshot(path=screenshot, full_page=True)
        assert not errors, errors
        evidence["viewports"].append(
            {
                "width": width,
                "files_controls": 0,
                "secret_ui": False,
                "page_errors": errors,
                "screenshot": str(screenshot),
            }
        )
        page.close()

    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    dialogs: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
    page.goto(f"{BASE}/enabled", wait_until="domcontentloaded")
    page.wait_for_function("document.documentElement.dataset.filesAdminReady === 'true'")
    page.locator("#app-loader").evaluate("element => element.remove()")
    page.locator("#rail-files").click()
    page.locator("#files-reauth-password").fill("qa-password")
    page.locator("#files-reauth-btn").click()
    page.locator("#files-admin-controls").wait_for(state="visible")
    page.get_by_role("button", name="FILE  safe-note.txt").wait_for()
    body_text = page.locator("#files-list").inner_text()
    assert "<img src=x onerror=alert(1)>.txt" in body_text
    assert page.locator("#files-list img").count() == 0
    assert not dialogs
    page.get_by_role("button", name="FILE  safe-note.txt").click()
    page.locator("#files-editor-textarea").wait_for(state="visible")
    assert page.locator("#files-editor-textarea").input_value() == "manual QA content\n"
    page.locator("#files-editor-close").click()
    screenshot = ROOT / "files-enabled-admin.png"
    page.screenshot(path=screenshot, full_page=True)
    assert not errors, errors
    evidence["enabled"] = {
        "capability_accepted": True,
        "hostile_filename_text": True,
        "injected_images": 0,
        "dialogs": dialogs,
        "safe_file_content": True,
        "page_errors": errors,
        "screenshot": str(screenshot),
    }
    page.close()
    browser.close()

(ROOT / "browser-evidence.json").write_text(
    json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
