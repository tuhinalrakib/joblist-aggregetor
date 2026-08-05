"""
Main CLI Entrypoint (main.py)
----------------------------
Orchestrates Job Listing Aggregation:
1. Optional session saving mode (`--save-session`)
2. Scraping job listings using Playwright (`--keyword`, `--location`, `--pages`, `--url`)
3. Cleaning and saving output to CSV/JSON using Pandas (`--output`)

Usage Examples:
---------------
# 1. Save Login Session first (Interactive window):
python main.py --save-session --url https://www.linkedin.com/login

# 2. Run Job Scraper with saved session:
python main.py --keyword "Python Developer" --location "Remote" --pages 2 --output jobs.csv

# 3. Test on open job boards (e.g., PythonJobs):
python main.py --url "https://pythonjobs.github.io/" --pages 1 --output python_jobs.csv
"""

import argparse
from pathlib import Path
from save_session import save_user_session
from scraper import JobScraper
from data_handler import JobDataHandler

def main():
    parser = argparse.ArgumentParser(
        description="Python Playwright Job Listing Aggregator"
        )
    
    parser.add_argument("--save-session", action="store_true", help="Launch browser to manually log in and save session to auth.json")
    parser.add_argument("--keyword", type=str, default="Python Developer", help="Job search keyword")
    parser.add_argument("--location", type=str, default="Remote", help="Job location")
    parser.add_argument("--pages", type=int, default=2, help="Number of pages to scrape")
    parser.add_argument("--url", type=str, default=None, help="Target URL to start scraping (optional override)")
    parser.add_argument("--auth-file", type=str, default="auth.json", help="Path to session JSON file")
    parser.add_argument("--output", type=str, default="jobs_output.csv", help="Output CSV filename")
    parser.add_argument("--no-headless", action="store_true", help="Run scraper browser in visible mode")

    args = parser.parse_args()

    # Step 1: Session save mode
    if args.save_session:
        target_login_url = args.url or "https://www.linkedin.com/login"
        save_user_session(target_login_url)
        return

    # Step 2: Determine target URL
    target_url = args.url
    if not target_url:
        import urllib.parse
        encoded_kw = urllib.parse.quote(args.keyword)
        encoded_loc = urllib.parse.quote(args.location)
        # Default to public job search URL (LinkedIn jobs search)
        target_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_kw}&location={encoded_loc}&sortBy=DD"
        print(f"[i] No custom URL specified. Searching LinkedIn Jobs for '{args.keyword}' in '{args.location}':")
        print(f"    {target_url}")

    # Step 3: Instantiate and run scraper
    scraper = JobScraper(
        keyword=args.keyword,
        location=args.location,
        max_pages=args.pages,
        auth_file=args.auth_file,
        headless=not args.no_headless
    )

    print(f"\n==========================================")
    print(f" JOB LISTING AGGREGATOR STARTED")
    print(f" Keyword: {args.keyword} | Location: {args.location}")
    print(f" Max Pages: {args.pages} | Output: {args.output}")
    print(f" Target URL: {target_url}")
    print(f"==========================================\n")

    raw_jobs = scraper.scrape_url(target_url)

    # Step 4: Data Processing & Cleaning & Export
    if raw_jobs:
        handler = JobDataHandler(raw_jobs)
        handler.save_to_csv(args.output)
        
        # Save JSON version
        json_output = Path(args.output).with_suffix(".json")
        handler.save_to_json(str(json_output))

        # Save HTML dashboard
        html_output = Path(args.output).with_suffix(".html")
        handler.save_to_html(str(html_output))

        # Render PDF report
        pdf_output = Path(args.output).with_suffix(".pdf")
        handler.save_to_pdf(str(pdf_output), str(html_output))
        
        print(f"\n[🎉] Complete! Reports available in CSV, JSON, HTML, and PDF format.")
    else:
        print("[!] No job listings were scraped. Please check target URL or CSS selectors.")

if __name__ == "__main__":
    main()
