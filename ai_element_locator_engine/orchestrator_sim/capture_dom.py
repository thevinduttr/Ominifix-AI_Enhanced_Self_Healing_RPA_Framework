from selenium import webdriver
import time

def capture_dom():
    driver = webdriver.Chrome()
    driver.get("https://example.com")
    time.sleep(3)

    html = driver.page_source
    with open("data/html/page_001.html", "w", encoding="utf-8") as f:
        f.write(html)

    driver.quit()

if __name__ == "__main__":
    capture_dom()
