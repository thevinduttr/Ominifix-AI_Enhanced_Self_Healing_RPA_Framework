from selenium import webdriver
from selenium.webdriver.common.by import By
import time

def run_bot():
    driver = webdriver.Chrome()
    driver.get("https://example.com")  # later replace with your own test app
    time.sleep(3)

    # ❌ This locator is intentionally WRONG
    driver.find_element(By.XPATH, "//button[@id='login_old']").click()

    driver.quit()

if __name__ == "__main__":
    run_bot()
