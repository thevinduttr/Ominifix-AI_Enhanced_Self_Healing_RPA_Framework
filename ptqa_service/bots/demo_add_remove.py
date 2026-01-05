from playwright.sync_api import sync_playwright


def run_main_flow():
    """
    Demo 1:
    Simple element add/remove test.
    Shows DOM clicking and assertion.
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://the-internet.herokuapp.com/add_remove_elements/", wait_until="networkidle")

        # Add element
        page.click("text=Add Element")

        delete_button = page.locator("button.added-manually")
        assert delete_button.count() > 0, "Delete button should appear"

        # Remove it
        delete_button.first.click()

        browser.close()
        return True
