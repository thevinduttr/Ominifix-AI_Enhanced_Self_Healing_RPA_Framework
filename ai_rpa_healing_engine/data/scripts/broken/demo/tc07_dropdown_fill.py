from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://crm.example.com/contacts/new")

        page.fill("#contact_name", "SLIIT Research Partner")

        # TC-07: Dropdown/select fill — broken aria-label (Region_old)
        page.fill("select[aria-label='Region_old']", "Western Province")

        page.click("#save-contact")
        browser.close()


if __name__ == "__main__":
    run()
