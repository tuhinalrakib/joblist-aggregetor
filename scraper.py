"""
Core Job Scraper Engine (scraper.py)
------------------------------------
Uses Playwright to navigate job listing websites, reuse saved auth sessions (`auth.json`),
extract job cards, and handle multi-page pagination.
"""

import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright, Page, BrowserContext

class JobScraper:
    def __init__(
        self,
        keyword: str = "Python Developer",
        location: str = "Remote",
        max_pages: int = 3,
        auth_file: Optional[str] = "auth.json",
        headless: bool = True
    ):
        self.keyword = keyword
        self.location = location
        self.max_pages = max_pages
        self.auth_file = Path(auth_file) if auth_file else None
        self.headless = headless
        self.scraped_jobs: List[Dict[str, Any]] = []

    def _get_context_options(self) -> dict:
        options = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        if self.auth_file and self.auth_file.exists():
            print(f"[+] Reusing saved session from: {self.auth_file.resolve()}")
            options["storage_state"] = str(self.auth_file)
        else:
            print("[!] No session file found or specified. Running in guest/unauthenticated mode.")
        return options

    def parse_job_cards_generic(self, page: Page) -> List[Dict[str, Any]]:
        """Extract job details using flexible CSS selectors supporting multiple job portals."""
        page_jobs = []

        # Comprehensive list of job card selectors across major job sites
        card_selectors = [
            ".job-card-container",
            ".base-card",
            ".job-search-card",
            ".job_seen_beacon",
            "div[data-job-id]",
            "div.job",
            "div[class*='job']",
            "li[class*='job']",
            ".job-tile",
            ".card-outline",
            "article",
            "li.job-result",
            "div.job-item",
            "tr.job-row",
            "td.company-col"
        ]
        
        cards = page.query_selector_all(", ".join(card_selectors))

        # Filter out empty or header containers if too generic
        valid_cards = []
        for card in cards:
            # Must have a link or heading
            if card.query_selector("h1, h2, h3, h4, a"):
                valid_cards.append(card)

        print(f"[+] Found {len(valid_cards)} job card elements on current page.")

        for idx, card in enumerate(valid_cards, 1):
            try:
                # Extract title
                title_elem = card.query_selector(
                    "h2, h3, h4, .job-card-list__title, .base-card__title, .job-title, a[class*='title'], a[title]"
                )
                title = title_elem.inner_text().strip() if title_elem else "N/A"

                # Extract company
                company_elem = card.query_selector(
                    "h4.base-search-card__subtitle, a.hidden-nested-link, .job-search-card__subtitle, .base-card__subtitle, .job-card-container__company-name, [data-tracking-control-name*='subtitle'], .company-name, [data-test*='company'], .company, [class*='company'], h4, span.info"
                )
                company = company_elem.inner_text().strip() if company_elem else "N/A"

                # Extract location
                location_elem = card.query_selector(
                    "span.job-search-card__location, .job-card-container__metadata-item, .job-search-card__location, .location, [data-test*='location'], .job-location, [class*='location']"
                )
                location = location_elem.inner_text().strip() if location_elem else self.location

                # Extract requirements / snippet / date / benefits
                req_elem = card.query_selector(
                    ".job-search-card__snippet, time.job-search-card__listdate, .result-benefits__text, .job-snippet, .summary, .description, .requirements, p.detail, p"
                )
                if req_elem and req_elem.inner_text().strip():
                    requirements = req_elem.inner_text().strip()
                else:
                    # Fallback metadata if snippet is absent
                    time_elem = card.query_selector("time")
                    time_str = time_elem.inner_text().strip() if time_elem else ""
                    requirements = f"Posted: {time_str}" if time_str else "Click 'Apply Now' for full details"

                # Extract job link
                link_elem = card.query_selector(
                    "a.base-card__full-link, a[class*='title'], a[href*='job'], a[href*='view'], h2 a, h3 a, a"
                )
                link = link_elem.get_attribute("href") if link_elem else "N/A"
                if link and link.startswith("/"):
                    # relative path conversion
                    base_domain = page.url.split("/")[2] if "/" in page.url else ""
                    link = f"https://{base_domain}{link}"

                # Only include valid job titles (ignoring generic headers)
                if title != "N/A" and len(title) > 2 and title.lower() not in ["home", "jobs", "about", "contact"]:
                    page_jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "requirements": requirements,
                        "link": link
                    })
            except Exception as e:
                print(f"[!] Error parsing job card {idx}: {e}")
                continue

        return page_jobs

    def auto_scroll(self, page: Page, max_scrolls: int = 4):
        """Scroll down smoothly to trigger lazy-loaded cards."""
        for _ in range(max_scrolls):
            page.evaluate("window.scrollBy(0, 500);")
            time.sleep(0.5)

    def scrape_url(self, target_url: str) -> List[Dict[str, Any]]:
        """Run Playwright scraper over target URL with pagination."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context_opts = self._get_context_options()
            context = browser.new_context(**context_opts)
            page = context.new_page()

            current_page_num = 1
            current_url = target_url

            while current_page_num <= self.max_pages:
                print(f"\n[+] Navigating to page {current_page_num}: {current_url}")
                try:
                    page.goto(current_url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(2)  # Allow dynamic content to load
                    self.auto_scroll(page)

                    # Extract listings
                    jobs = self.parse_job_cards_generic(page)
                    self.scraped_jobs.extend(jobs)

                    # Pagination: check for Next button or page link
                    next_button = page.query_selector(
                        "a[aria-label*='Next'], button[aria-label*='Next'], a.next, .pagination-next, [data-test='pagination-next']"
                    )

                    if next_button and current_page_num < self.max_pages:
                        is_disabled = next_button.get_attribute("disabled") or "disabled" in (next_button.get_attribute("class") or "")
                        if not is_disabled:
                            next_href = next_button.get_attribute("href")
                            if next_href:
                                if next_href.startswith("/"):
                                    base_domain = page.url.split("/")[2]
                                    current_url = f"https://{base_domain}{next_href}"
                                else:
                                    current_url = next_href
                                current_page_num += 1
                                continue
                            else:
                                next_button.click()
                                time.sleep(3)
                                current_page_num += 1
                                continue

                    # If no clickable next button, break loop
                    print("[+] Reached last available page or no next pagination button found.")
                    break

                except Exception as e:
                    print(f"[!] Error on page {current_page_num}: {e}")
                    break

            browser.close()

        print(f"\n[✔] Scraping complete! Total jobs collected: {len(self.scraped_jobs)}")
        return self.scraped_jobs
