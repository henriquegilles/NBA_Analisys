"""
Shared Selenium/Chrome setup for Basketball Reference scrapers.

BBR actively blocks plain HTTP requests (403/429) and headless Chromium
(Cloudflare bot protection). We use selenium-stealth to hide automation
signatures. On WSL with the Chromium snap package the browser binary and
the bundled chromedriver live in different paths than what webdriver-manager
expects — we hard-code both to skip the version mismatch problem.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth

# Chromium snap paths on Ubuntu/WSL
CHROME_BINARY = "/usr/bin/chromium-browser"
CHROMEDRIVER_PATH = "/snap/bin/chromium.chromedriver"

# Seconds to wait after page load before scraping.
# WebDriverWait on BBR's div#wrap is unreliable (they rate-limit the selector).
PAGE_LOAD_SLEEP = 8


def build_driver() -> webdriver.Chrome:
    """Return a headless Chrome WebDriver with stealth patches applied."""
    opts = Options()
    opts.binary_location = CHROME_BINARY
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=opts)

    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
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
