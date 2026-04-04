"""
Shared Selenium/Chrome setup for Basketball Reference scrapers.

BBR actively blocks plain HTTP requests (403/429), so we drive a
headless Chromium instance. On WSL with the Chromium snap package the
browser binary and the bundled chromedriver live in different paths than
what webdriver-manager expects — we hard-code both to skip the version
mismatch problem.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Chromium snap paths on Ubuntu/WSL
CHROME_BINARY = "/usr/bin/chromium-browser"
CHROMEDRIVER_PATH = "/snap/bin/chromium.chromedriver"

# Seconds to wait after page load before scraping.
# WebDriverWait on BBR's div#wrap is unreliable (they rate-limit the selector).
PAGE_LOAD_SLEEP = 8


def build_driver() -> webdriver.Chrome:
    """Return a headless Chrome WebDriver ready to scrape BBR."""
    opts = Options()
    opts.binary_location = CHROME_BINARY
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")

    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=opts)
    return driver


def fetch_page(url: str) -> webdriver.Chrome:
    """
    Open *url* in a new headless Chrome session and return the driver.
    Caller is responsible for calling driver.quit() when done.
    """
    driver = build_driver()
    driver.get(url)
    time.sleep(PAGE_LOAD_SLEEP)
    return driver
