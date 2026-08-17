"""
FastAPI Backend Application (app.py)
-----------------------------------
Full-stack backend server for AI-Powered Job Listing Aggregator & Intelligence Platform.
Serves the web dashboard UI, provides REST API endpoints for:
- Playwright / BeautifulSoup scraping
- Google Gemini AI Summarization & Tech Stack Extraction
- Resume & Candidate Skills Matcher (Match Score %)
- Market Analytics & Tech Demand Insights (Chart.js)
- Multi-format file exports (CSV, PDF, JSON)

Run Server:
-----------
uvicorn app:app --reload --port 8000
"""

import os
import tempfile
import time
import json
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from scraper import JobScraper
from data_handler import JobDataHandler
from ai_handler import AIJobHandler

app = FastAPI(title="AI Job Listing Aggregator & Intelligence API", version="3.0.0")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "templates" / "index.html"

# Initialize AI Handler
ai_engine = AIJobHandler()

# Use system temp directory on Serverless (e.g. Vercel) where root filesystem is read-only
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    STORAGE_DIR = Path(tempfile.gettempdir())
else:
    STORAGE_DIR = BASE_DIR

OUTPUT_CSV = STORAGE_DIR / "jobs_output.csv"
OUTPUT_JSON = STORAGE_DIR / "jobs_output.json"
OUTPUT_HTML = STORAGE_DIR / "jobs_output.html"
OUTPUT_PDF = STORAGE_DIR / "jobs_output.pdf"

# Search Query Cache with TTL (10 minutes)
CACHE_TTL_SECONDS = 600
SEARCH_CACHE: Dict[str, Dict[str, Any]] = {}
LATEST_JOBS_CACHE: List[Dict[str, Any]] = []

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
    location: str = "Worldwide"
    workplace_type: Optional[str] = "all"
    experience_level: Optional[str] = "all"
    max_pages: int = 2
    platform: Optional[str] = "linkedin"
    url: Optional[str] = None
    auth_file: Optional[str] = "auth.json"

class AIAnalyzeRequest(BaseModel):
    jobs: Optional[List[Dict[str, Any]]] = None
    api_key: Optional[str] = None

class AIMatchRequest(BaseModel):
    candidate_skills: Optional[List[str]] = []
    resume_text: Optional[str] = None
    jobs: Optional[List[Dict[str, Any]]] = None

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serve the Web UI frontend."""
    if not TEMPLATE_PATH.exists():
        raise HTTPException(status_code=404, detail="Template index.html not found.")
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/scrape")
def trigger_scrape(req: ScrapeRequest):
    """Execute Playwright job scraper with caching, AI tech stack enrichment and fast response time."""
    global LATEST_JOBS_CACHE
    platform_name = (req.platform or "linkedin").strip().lower()
    cache_key = f"{req.keyword.strip().lower()}|{(req.location or '').strip().lower()}|{req.workplace_type}|{req.experience_level}|{req.max_pages}|{platform_name}|{req.url or ''}"
    now = time.time()

    # Check TTL cache for instant return
    if cache_key in SEARCH_CACHE:
        cached_item = SEARCH_CACHE[cache_key]
        if now - cached_item["timestamp"] < CACHE_TTL_SECONDS:
            print(f"[+] Serving cached search results for query key: {cache_key}")
            LATEST_JOBS_CACHE = cached_item["jobs"]
            return {
                "success": True,
                "count": cached_item["count"],
                "jobs": cached_item["jobs"],
                "from_cache": True
            }

    target_url = req.url
    if not target_url or not target_url.strip():
        search_kw = req.keyword
        wp_val = str(req.workplace_type or "").strip().lower()
        if wp_val == "remote" and "remote" not in search_kw.lower():
            search_kw = f"{search_kw} Remote"

        encoded_kw = urllib.parse.quote(search_kw)
        encoded_loc = urllib.parse.quote(req.location or "Worldwide")

        if platform_name == "glassdoor":
            target_url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={encoded_kw}&locKeyword={encoded_loc}"
        elif platform_name == "indeed":
            target_url = f"https://www.indeed.com/jobs?q={encoded_kw}&l={encoded_loc}"
        else: # Default: LinkedIn
            target_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_kw}&location={encoded_loc}&sortBy=DD"
            
            # Add Workplace Type filter (f_WT: 1=On-site, 2=Remote, 3=Hybrid)
            wt_code = WORKPLACE_MAP.get(wp_val)
            if wt_code:
                target_url += f"&f_WT={wt_code}"

            # Add Experience Level filter if specified
            exp_code = EXP_LEVEL_MAP.get(str(req.experience_level).lower())
            if exp_code:
                target_url += f"&f_E={exp_code}"

    print(f"\n[+] API Scraping Triggered:")
    print(f"    Keyword: '{req.keyword}' | Location: '{req.location}' | Workplace Type: '{req.workplace_type}' | Experience Level: '{req.experience_level}' | Pages: {req.max_pages}")
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
    cleaned_df = handler.clean_data(experience_level=req.experience_level, workplace_type=req.workplace_type)
    jobs_list = cleaned_df.to_dict(orient="records")

    # Fast initial enrichment: Extract tech stack, experience level and heuristic summary
    for job in jobs_list:
        title = job.get("title", "")
        req_text = job.get("requirements", "")
        company = job.get("company", "")
        skills = ai_engine.extract_tech_stack_offline(f"{title} {req_text}")
        job["tech_stack"] = skills
        job["experience_level"] = ai_engine.detect_experience_level_offline(title, req_text)
        job["ai_summary"] = ai_engine.generate_heuristic_summary(title, company, skills, req_text)

    # Export to CSV, JSON, and HTML immediately (fast)
    handler.save_to_csv(str(OUTPUT_CSV))
    handler.save_to_json(str(OUTPUT_JSON))
    handler.save_to_html(str(OUTPUT_HTML))

    LATEST_JOBS_CACHE = jobs_list

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

@app.post("/api/ai/analyze")
def ai_analyze_jobs(req: AIAnalyzeRequest):
    """
    Analyzes jobs using Google Gemini API (or hybrid NLP).
    Extracts tech stack, experience level, and 2-line AI summary.
    """
    global LATEST_JOBS_CACHE
    jobs_to_analyze = req.jobs or LATEST_JOBS_CACHE

    if not jobs_to_analyze:
        # Try to load from OUTPUT_JSON if memory cache is empty
        if OUTPUT_JSON.exists():
            try:
                with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                    jobs_to_analyze = json.load(f)
            except Exception:
                jobs_to_analyze = []

    if not jobs_to_analyze:
        raise HTTPException(status_code=400, detail="No jobs available to analyze. Please scrape jobs first.")

    enriched = ai_engine.batch_enrich_jobs(jobs_to_analyze, custom_api_key=req.api_key)
    LATEST_JOBS_CACHE = enriched

    # Update stored files with enriched data
    try:
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(enriched, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[!] Warning updating JSON cache: {e}")

    return {
        "success": True,
        "count": len(enriched),
        "jobs": enriched
    }

@app.post("/api/ai/match")
def match_candidate_skills(req: AIMatchRequest):
    """
    Calculates candidate match score (%) for each job based on input skills or resume text.
    """
    jobs_to_match = req.jobs or LATEST_JOBS_CACHE

    if not jobs_to_match and OUTPUT_JSON.exists():
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                jobs_to_match = json.load(f)
        except Exception:
            jobs_to_match = []

    if not jobs_to_match:
        raise HTTPException(status_code=400, detail="No jobs found to match against. Please run a job search first.")

    matched_results = []
    total_score = 0

    for job in jobs_to_match:
        job_copy = dict(job)
        match_info = ai_engine.calculate_match_score(
            job=job_copy,
            candidate_skills=req.candidate_skills or [],
            resume_text=req.resume_text
        )
        job_copy["match_score"] = match_info["match_score"]
        job_copy["matched_skills"] = match_info["matched_skills"]
        job_copy["missing_skills"] = match_info["missing_skills"]
        matched_results.append(job_copy)
        total_score += match_info["match_score"]

    avg_score = round(total_score / len(matched_results), 1) if matched_results else 0.0

    return {
        "success": True,
        "count": len(matched_results),
        "average_match_score": avg_score,
        "jobs": matched_results
    }

@app.post("/api/analytics")
def get_analytics(jobs: Optional[List[Dict[str, Any]]] = Body(None)):
    """
    Computes market intelligence & skill demand statistics for Chart.js.
    """
    target_jobs = jobs or LATEST_JOBS_CACHE

    if not target_jobs and OUTPUT_JSON.exists():
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                target_jobs = json.load(f)
        except Exception:
            target_jobs = []

    analytics = ai_engine.generate_market_analytics(target_jobs or [])
    return {
        "success": True,
        "analytics": analytics
    }

@app.get("/api/download/csv")
def download_csv():
    """Download scraped jobs as CSV."""
    if not OUTPUT_CSV.exists():
        raise HTTPException(status_code=404, detail="No CSV output file found. Run a search first.")
    return FileResponse(path=str(OUTPUT_CSV), media_type="text/csv", filename="scraped_jobs.csv")

@app.get("/api/download/pdf")
def download_pdf():
    """Download scraped jobs as PDF (or HTML report if headless PDF engine is unavailable)."""
    if not OUTPUT_JSON.exists():
        raise HTTPException(status_code=404, detail="No search data found. Run a job search first.")
    
    # If PDF is missing or stale compared to JSON, generate it on demand
    if not OUTPUT_PDF.exists() or (OUTPUT_JSON.exists() and OUTPUT_PDF.stat().st_mtime < OUTPUT_JSON.stat().st_mtime):
        print("[+] Generating PDF report on-demand...")
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            jobs_data = json.load(f)
        handler = JobDataHandler(jobs_data)
        handler.save_to_pdf(str(OUTPUT_PDF), str(OUTPUT_HTML))

    if OUTPUT_PDF.exists():
        return FileResponse(path=str(OUTPUT_PDF), media_type="application/pdf", filename="scraped_jobs.pdf")
    elif OUTPUT_HTML.exists():
        return FileResponse(path=str(OUTPUT_HTML), media_type="text/html", filename="scraped_jobs_report.html")
    else:
        raise HTTPException(status_code=404, detail="Report file not found.")

@app.get("/api/download/json")
def download_json():
    """Download scraped jobs as JSON."""
    if not OUTPUT_JSON.exists():
        raise HTTPException(status_code=404, detail="No JSON output file found. Run a search first.")
    return FileResponse(path=str(OUTPUT_JSON), media_type="application/json", filename="scraped_jobs.json")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
