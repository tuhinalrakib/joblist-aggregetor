"""
FastAPI Backend Application (app.py)
-----------------------------------
Full-stack backend server for Job Listing Aggregator.
Serves the web dashboard UI and provides REST API endpoints for scraping and exporting files (CSV, PDF, JSON).

Run Server:
-----------
uvicorn app:app --reload --port 8000
"""

import time
import json
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from scraper import JobScraper
from data_handler import JobDataHandler

app = FastAPI(title="Job Listing Aggregator API", version="2.0.0")

BASE_DIR = Path(__file__).parent
TEMPLATE_PATH = BASE_DIR / "templates" / "index.html"
OUTPUT_CSV = BASE_DIR / "jobs_output.csv"
OUTPUT_JSON = BASE_DIR / "jobs_output.json"
OUTPUT_HTML = BASE_DIR / "jobs_output.html"
OUTPUT_PDF = BASE_DIR / "jobs_output.pdf"

# Search Query Cache with TTL (10 minutes)
CACHE_TTL_SECONDS = 600
SEARCH_CACHE: Dict[str, Dict[str, Any]] = {}

WORKPLACE_MAP = {
    "onsite": "1",
    "on-site": "1",
    "remote": "2",
    "hybrid": "3",
}

EXP_LEVEL_MAP = {
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "internship": "1",
    "entry": "2",
    "associate": "3",
    "mid_senior": "4",
    "director": "5",
    "executive": "6",
}

class ScrapeRequest(BaseModel):
    keyword: str = "React Developer"
    location: str = "Remote"
    experience_level: Optional[str] = "all"
    max_pages: int = 2
    platform: Optional[str] = "linkedin"
    url: Optional[str] = None
    auth_file: Optional[str] = "auth.json"

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serve the Web UI frontend."""
    if not TEMPLATE_PATH.exists():
        raise HTTPException(status_code=404, detail="Template index.html not found.")
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/scrape")
def trigger_scrape(req: ScrapeRequest):
    """Execute Playwright job scraper with caching and fast response time."""
    platform_name = (req.platform or "linkedin").strip().lower()
    cache_key = f"{req.keyword.strip().lower()}|{req.location.strip().lower()}|{req.experience_level}|{req.max_pages}|{platform_name}|{req.url or ''}"
    now = time.time()

    # Check TTL cache for instant return
    if cache_key in SEARCH_CACHE:
        cached_item = SEARCH_CACHE[cache_key]
        if now - cached_item["timestamp"] < CACHE_TTL_SECONDS:
            print(f"[+] Serving cached search results for query key: {cache_key}")
            return {
                "success": True,
                "count": cached_item["count"],
                "jobs": cached_item["jobs"],
                "from_cache": True
            }

    target_url = req.url
    if not target_url or not target_url.strip():
        encoded_kw = urllib.parse.quote(req.keyword)
        encoded_loc = urllib.parse.quote(req.location)

        if platform_name == "glassdoor":
            target_url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={encoded_kw}&locKeyword={encoded_loc}"
        elif platform_name == "indeed":
            target_url = f"https://www.indeed.com/jobs?q={encoded_kw}&l={encoded_loc}"
        else: # Default: LinkedIn
            target_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_kw}&location={encoded_loc}&sortBy=DD"
            
            # Add Workplace Type filter (f_WT: 1=On-site, 2=Remote, 3=Hybrid)
            wt_code = WORKPLACE_MAP.get(str(req.location).strip().lower())
            if wt_code:
                target_url += f"&f_WT={wt_code}"

            # Add Experience Level filter if specified
            exp_code = EXP_LEVEL_MAP.get(str(req.experience_level).lower())
            if exp_code:
                target_url += f"&f_E={exp_code}"

    print(f"\n[+] API Scraping Triggered:")
    print(f"    Keyword: '{req.keyword}' | Location: '{req.location}' | Experience Level: '{req.experience_level}' | Pages: {req.max_pages}")
    print(f"    Target URL: {target_url}")

    scraper = JobScraper(
        keyword=req.keyword,
        location=req.location,
        max_pages=req.max_pages,
        auth_file=req.auth_file,
        headless=True
    )

    raw_jobs = scraper.scrape_url(target_url)

    if not raw_jobs:
        return {"success": False, "message": "No jobs found.", "jobs": [], "from_cache": False}

    handler = JobDataHandler(raw_jobs)
    cleaned_df = handler.clean_data(experience_level=req.experience_level)
    jobs_list = cleaned_df.to_dict(orient="records")

    # Export to CSV, JSON, and HTML immediately (fast)
    handler.save_to_csv(str(OUTPUT_CSV))
    handler.save_to_json(str(OUTPUT_JSON))
    handler.save_to_html(str(OUTPUT_HTML))

    # Note: PDF generation is deferred to on-demand download endpoint (/api/download/pdf)
    # Store results in cache
    SEARCH_CACHE[cache_key] = {
        "timestamp": now,
        "count": len(jobs_list),
        "jobs": jobs_list
    }

    return {
        "success": True,
        "count": len(jobs_list),
        "jobs": jobs_list,
        "from_cache": False
    }

@app.get("/api/download/csv")
def download_csv():
    """Download scraped jobs as CSV."""
    if not OUTPUT_CSV.exists():
        raise HTTPException(status_code=404, detail="No CSV output file found. Run a search first.")
    return FileResponse(path=str(OUTPUT_CSV), media_type="text/csv", filename="scraped_jobs.csv")

@app.get("/api/download/pdf")
def download_pdf():
    """Download scraped jobs as PDF (rendered on-demand if required)."""
    if not OUTPUT_JSON.exists():
        raise HTTPException(status_code=404, detail="No search data found. Run a job search first.")
    
    # If PDF is missing or stale compared to JSON, generate it on demand
    if not OUTPUT_PDF.exists() or OUTPUT_PDF.stat().st_mtime < OUTPUT_JSON.stat().st_mtime:
        print("[+] Generating PDF report on-demand...")
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            jobs_data = json.load(f)
        handler = JobDataHandler(jobs_data)
        handler.save_to_pdf(str(OUTPUT_PDF), str(OUTPUT_HTML))

    return FileResponse(path=str(OUTPUT_PDF), media_type="application/pdf", filename="scraped_jobs.pdf")

@app.get("/api/download/json")
def download_json():
    """Download scraped jobs as JSON."""
    if not OUTPUT_JSON.exists():
        raise HTTPException(status_code=404, detail="No JSON output file found. Run a search first.")
    return FileResponse(path=str(OUTPUT_JSON), media_type="application/json", filename="scraped_jobs.json")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)

