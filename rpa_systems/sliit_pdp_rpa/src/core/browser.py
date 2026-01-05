from playwright.sync_api import sync_playwright

def launch_browser(headless: bool, slow_mo_ms: int):
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless, slow_mo=slow_mo_ms)
    context = browser.new_context()
    page = context.new_page()
    return pw, browser, context, page
