from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://shop.example.com/cart")

        # Fill shipping address
        page.fill("#address-line1", "123 Main St")

        # BROKEN: submit button ID changed on the website
        page.click("#submit-order")

        page.wait_for_timeout(3000)
        browser.close()


if __name__ == "__main__":
    run()
