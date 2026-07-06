"""
Google Scholar scraper for a professor's publications.

This module wraps the original Selenium scraping script into a reusable
function. Core scraping mechanics (selectors, waits, captcha handling,
detail-page click-back loop) are preserved as-is from the original script.
Only the following changes were made for Flask integration:
  - Wrapped in a function taking `professor_name` as a parameter.
  - Driver is created/quit inside the function (try/finally) to avoid
    leaking Chrome processes on request errors.
  - Removed module-level logging.basicConfig (app.py configures logging).
  - Removed CSV output; returns a list of dicts in memory.
  - Added custom exceptions for profile-not-found / no-publications / generic
    scraper errors, so Flask can show user-friendly messages.
  - Citation count (`cited_by`) is now read directly from the profile's
    publication row (td.gsc_a_c a) instead of the detail page, since Google
    Scholar does not reliably expose citation count on the detail page.
"""

import random
import time
import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

logger = logging.getLogger(__name__)

DRIVER_PATH = r"chromedriver.exe"
SCHOLAR_URL = "https://scholar.google.com/"
TARGET_COUNT = 100
MAX_SHOW_MORE_ATTEMPTS = 15


class ScraperError(Exception):
    """Generic scraper failure (unexpected Selenium/browser issue)."""
    pass


class ProfileNotFoundError(ScraperError):
    """Raised when the professor's Google Scholar profile cannot be found."""
    pass


class NoPublicationsError(ScraperError):
    """Raised when a profile is found but has no publications listed."""
    pass


def scrape_professor_publications(professor_name: str) -> list[dict]:
    """
    Scrape a professor's Google Scholar publications.

    Args:
        professor_name: Name to search for on Google Scholar.

    Returns:
        List of dicts: {"title": str, "link": str, "description": str, "cited_by": str}

    Raises:
        ProfileNotFoundError: if no matching profile is found.
        NoPublicationsError: if the profile has zero publications.
        ScraperError: for other unexpected scraping failures.
    """
    service = Service(executable_path=DRIVER_PATH)
    driver = webdriver.Chrome(service=service)

    def wait_for_captcha():
        """Robust CAPTCHA check that never crashes on stale/loading pages."""
        while True:
            try:
                current_url = driver.current_url
                page_src = driver.page_source.lower()
            except Exception:
                time.sleep(1)
                continue
            if "sorry" in current_url or "recaptcha" in page_src:
                logger.warning("CAPTCHA detected. Waiting for manual solve.")
                input("Press Enter here in the terminal once solved and the page has loaded...")
                logger.info("CAPTCHA solved, resuming.")
            else:
                break

    def safe_find(by, value, retries=2):
        """find_element wrapped with captcha recovery."""
        for attempt in range(retries + 1):
            try:
                return driver.find_element(by, value)
            except Exception:
                logger.warning(f"Element not found ({value}), attempt {attempt+1}. Checking for captcha.")
                wait_for_captcha()
                if attempt == retries:
                    raise

    publications = []

    try:
        driver.get(SCHOLAR_URL)
        driver.maximize_window()
        logger.info("Opened Google Scholar homepage.")
        time.sleep(random.uniform(5, 12))

        wait_for_captcha()

        try:
            search_box = safe_find(By.XPATH, '''//*[@id="gs_hdr_frm"]/div''')
            search_box.click()
            logger.info("Clicked search box.")
            time.sleep(random.uniform(5, 12))

            input_search_box = safe_find(By.XPATH, '''//*[@id="gs_hdr_tsi"]''')
            input_search_box.send_keys(professor_name, Keys.RETURN)
            logger.info("Submitted search query.")
            time.sleep(random.uniform(5, 12))
        except Exception as e:
            raise ScraperError(f"Failed to submit search query on Google Scholar: {e}")

        wait_for_captcha()

        try:
            div_profile = safe_find(By.XPATH, '''//*[@id="gs_res_ccl_mid"]/div[1]/table/tbody/tr/td[2]/h4/a''')
            div_profile.click()
            logger.info("Clicked profile link.")
            time.sleep(random.uniform(5, 12))
        except Exception as e:
            raise ProfileNotFoundError(
                f"Could not find a Google Scholar profile for '{professor_name}'."
            ) from e

        wait_for_captcha()

        try:
            div_sort_year = safe_find(By.XPATH, '''//*[@id="gsc_a_ha"]/a''')
            div_sort_year.click()
            logger.info("Sorted publications by year.")
            time.sleep(random.uniform(5, 12))
        except Exception as e:
            raise ScraperError(f"Failed to sort publications by year: {e}")

        # ---------------- Load publications: keep clicking "Show more" ----------------
        for attempt in range(MAX_SHOW_MORE_ATTEMPTS):
            rows = driver.find_elements(By.CSS_SELECTOR, "#gsc_a_b .gsc_a_tr")
            logger.info(f"Currently loaded rows: {len(rows)}")
            if len(rows) >= TARGET_COUNT:
                break
            try:
                show_more = driver.find_element(By.ID, "gsc_bpf_more")
                if show_more.is_enabled() and show_more.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", show_more)
                    time.sleep(1)
                    show_more.click()
                    logger.info("Clicked 'Show more' button.")
                    time.sleep(random.uniform(3, 6))
                else:
                    logger.info("'Show more' button disabled — no more publications.")
                    break
            except Exception:
                logger.warning("'Show more' button not found. Trying to check for captcha.")
                wait_for_captcha()
                break

        rows = driver.find_elements(By.CSS_SELECTOR, "#gsc_a_b .gsc_a_tr")
        num_rows = min(len(rows), TARGET_COUNT)
        logger.info(f"Total rows available for scraping: {num_rows}")

        if num_rows == 0:
            raise NoPublicationsError(
                f"No publications found for '{professor_name}'."
            )

        # ---------------- Scrape each publication ----------------
        for i in range(num_rows):
            logger.info(f"Processing publication {i+1}/{num_rows}")
            try:
                rows = driver.find_elements(By.CSS_SELECTOR, "#gsc_a_b .gsc_a_tr")
                row = rows[i]

                title_el = row.find_element(By.CSS_SELECTOR, ".gsc_a_at")
                title = title_el.text
                link = title_el.get_attribute("href")


                try:
                    citation_el = row.find_element(By.CSS_SELECTOR, "td.gsc_a_c a")
                    cited_by = citation_el.text.strip()
                except Exception:
                    cited_by = ""

                title_el.click()
                time.sleep(2)
                WebDriverWait(driver, 10).until(
                    ec.presence_of_element_located((By.ID, "gsc_oci_title"))
                )
            except Exception as e:
                logger.error(f"Failed to open publication {i+1}: {e}")
                wait_for_captcha()
                driver.back()
                time.sleep(2)
                continue

            wait_for_captcha()

            description = ""
            try:
                description = driver.find_element(By.ID, "gsc_oci_descr").text
                if not description.strip():
                    raise Exception("Description is empty")
            except Exception:
                logger.warning(f"No description for publication {i+1}: '{title}'. Skipping.")
                driver.back()
                time.sleep(2)
                WebDriverWait(driver, 10).until(
                    ec.presence_of_element_located((By.CSS_SELECTOR, "#gsc_a_b .gsc_a_tr"))
                )
                continue

            publications.append({
                "title": title,
                "link": link,
                "description": description,
                "cited_by": cited_by
            })
            logger.info(f"Successfully scraped: '{title}' (cited_by: '{cited_by}')")

            driver.back()
            time.sleep(2)
            WebDriverWait(driver, 10).until(
                ec.presence_of_element_located((By.CSS_SELECTOR, "#gsc_a_b .gsc_a_tr"))
            )

        logger.info(f"Scraping complete. Total publications scraped: {len(publications)}")

        if not publications:
            raise NoPublicationsError(
                f"Found a profile for '{professor_name}' but could not scrape any usable publications "
                f"(all had missing descriptions or failed to load)."
            )

        return publications

    except ScraperError:
        raise
    except Exception as e:
        logger.exception("Unexpected error during scraping.")
        raise ScraperError(f"Unexpected scraping failure: {e}") from e
    finally:
        driver.quit()
        logger.info("Driver closed.")
