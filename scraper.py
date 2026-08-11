"""
Core Job Scraper Engine (scraper.py)
------------------------------------
Uses Playwright Async API to navigate job listing websites concurrently in parallel tabs.
Applies aggressive network resource blocking (images, media, fonts, stylesheets, analytics)
and fast browser JS evaluation for ultra-fast scraping.
"""

import asyncio
import json
import re
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page, BrowserContext

class JobScraper:
    def __init__(
        self,
        keyword: str = "Python Developer",
        location: str = "Remote",
        max_pages: int = 2,
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
            print("[!] Running in guest/unauthenticated mode.")
        return options

    def _generate_page_urls(self, target_url: str) -> List[str]:
        """Generate parallel page URLs based on start offset pagination."""
        if self.max_pages <= 1:
            return [target_url]
        
        urls = []
        for p in range(self.max_pages):
            start_offset = p * 25
            if "start=" in target_url:
                url = re.sub(r'start=\d+', f'start={start_offset}', target_url)
            elif "?" in target_url:
                url = f"{target_url}&start={start_offset}"
            else:
                url = f"{target_url}?start={start_offset}"
            urls.append(url)
        return urls

    async def _parse_job_cards_fast(self, page: Page) -> List[Dict[str, Any]]:
        """Fast extraction using browser JS execution in 1 millisecond."""
        default_loc = self.location
        js_script = f"""
        () => {{
            const cardSelectors = [
                ".job-card-container", ".base-card", ".job-search-card",
                ".job_seen_beacon", "div[data-job-id]", "div.job",
                "div[class*='job']", "li[class*='job']", ".job-tile",
                "[data-test*='job']", "[class*='jobListing']", "[class*='JobCard']",
                "[class*='jobListItem']", ".JobCard_jobCardContainer",
                ".card-outline", "article", "li.job-result", "div.job-item",
                "tr.job-row", "td.company-col"
            ];
            const cards = Array.from(document.querySelectorAll(cardSelectors.join(",")));
            const results = [];
            const fallbackLocation = {json.dumps(default_loc)};

            cards.forEach(card => {{
                if (!card.querySelector("h1, h2, h3, h4, a")) return;

                // Title
                const titleElem = card.querySelector("h2, h3, h4, [data-test*='title'], [class*='JobTitle'], .job-card-list__title, .base-card__title, .job-title, a[class*='title'], a[title]");
                const title = titleElem ? titleElem.innerText.trim() : "";

                // Company
                const companyElem = card.querySelector("[data-test*='employer'], [data-test*='company'], [class*='EmployerName'], h4.base-search-card__subtitle, a.hidden-nested-link, .job-search-card__subtitle, .base-card__subtitle, .job-card-container__company-name, [data-tracking-control-name*='subtitle'], .company-name, .company, [class*='company'], h4, span.info");
                const company = companyElem ? companyElem.innerText.trim() : "Featured Employer";

                // Location
                const locationElem = card.querySelector("[data-test*='location'], [class*='Location'], span.job-search-card__location, .job-card-container__metadata-item, .job-search-card__location, .location, .job-location, [class*='location']");
                let location = locationElem ? locationElem.innerText.trim() : "";
                if (!location) location = fallbackLocation;

                // Workplace Type (Remote, On-site, Hybrid)
                const wpElem = card.querySelector(".job-search-card__workplace-type, [class*='workplace-type'], [class*='workplaceType'], .job-card-container__metadata-item--workplace-type");
                let workplace_type = wpElem ? wpElem.innerText.trim() : "";

                // Date
                const timeElem = card.querySelector("time.job-search-card__listdate, time, .job-search-card__listdate, [class*='date']");
                const date_posted = timeElem ? timeElem.innerText.trim() : "Recently";

                // Requirements / snippet
                const reqElem = card.querySelector(".job-search-card__snippet, .result-benefits__text, .job-snippet, .summary, .description, .requirements, p.detail");
                let requirements = reqElem ? reqElem.innerText.trim() : "";
                if (!requirements) {{
                    requirements = date_posted !== "Recently" ? `Posted: ${{date_posted}}` : "Click 'Apply Now' for full details";
                }}

                // Link
                const linkElem = card.querySelector("a.base-card__full-link, a[class*='title'], a[href*='job'], a[href*='view'], h2 a, h3 a, a");
                let link = linkElem ? linkElem.getAttribute("href") : "N/A";
                if (link && link.startsWith("/")) {{
                    link = window.location.origin + link;
                }}

                if (title && title.length > 2 && !["home", "jobs", "about", "contact"].includes(title.toLowerCase())) {{
                    results.push({{ title, company, location, workplace_type, date_posted, requirements, link }});
                }}
            }});
            return results;
        }}
        """
        try:
            return await page.evaluate(js_script)
        except Exception as e:
            print(f"[!] Error executing JS evaluation: {e}")
            return []

    async def _scrape_single_page(self, context: BrowserContext, page_num: int, url: str) -> List[Dict[str, Any]]:
        """Scrape a single URL in an isolated tab with resource interceptors."""
        page = await context.new_page()

        # Aggressive resource blocking (images, media, fonts, stylesheets, analytics)
        async def route_interceptor(route):
            req = route.request
            if req.resource_type in ["image", "media", "font", "stylesheet"]:
                await route.abort()
            elif any(d in req.url for d in ["google-analytics", "doubleclick", "facebook", "analytics", "telemetry", "linkedin.com/li/track"]):
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", route_interceptor)

        print(f"[+] [Tab {page_num}] Navigating: {url}")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=12000)
            
            # Quick wait for job container or continue immediately
            try:
                await page.wait_for_selector(
                    ".job-card-container, .base-card, .job-search-card, div[data-job-id], ul.jobs-search__results-list",
                    timeout=2500
                )
            except Exception:
                pass

            # Fast auto-scroll to trigger lazy-loaded nodes
            await page.evaluate("window.scrollBy(0, 1000);")
            await asyncio.sleep(0.1)

            jobs = await self._parse_job_cards_fast(page)
            print(f"[✔] [Tab {page_num}] Extracted {len(jobs)} job cards.")
            await page.close()
            return jobs
        except Exception as e:
            print(f"[!] [Tab {page_num}] Scraping warning: {e}")
            try:
                await page.close()
            except Exception:
                pass
            return []

    async def _async_scrape_all(self, target_url: str) -> List[Dict[str, Any]]:
        """Launch browser and scrape all requested pages in parallel tabs."""
        urls = self._generate_page_urls(target_url)
        print(f"[⚡] Concurrent Scraper Mode: Scraping {len(urls)} pages in parallel tabs...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context_opts = self._get_context_options()
            context = await browser.new_context(**context_opts)

            tasks = [self._scrape_single_page(context, idx + 1, url) for idx, url in enumerate(urls)]
            page_results = await asyncio.gather(*tasks)

            await browser.close()

            all_jobs = []
            for jobs in page_results:
                all_jobs.extend(jobs)

            self.scraped_jobs = all_jobs
            print(f"[✔] Scraping completed in parallel! Total jobs collected: {len(all_jobs)}")
            return all_jobs

    def scrape_url(self, target_url: str) -> List[Dict[str, Any]]:
        """Synchronous wrapper method compatible with CLI and FastAPI backend."""
        def run_worker():
            return asyncio.run(self._async_scrape_all(target_url))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_worker)
            return future.result()
