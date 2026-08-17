"""
AI Job Intelligence Handler (ai_handler.py)
--------------------------------------------
Handles:
1. Tech Stack & Experience Level Extraction
2. AI Job Description Summarizer (via Google Gemini API with smart offline NLP fallback)
3. "Match My Resume / Skills" scoring engine
4. Market Analytics & In-Demand Technology Aggregator
"""

import os
import re
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional, Set

try:
    import requests
except ImportError:
    requests = None

# Comprehensive Tech Stack Taxonomy for High-Precision Offline / Hybrid Extraction
COMMON_TECH_SKILLS = [
    # Frontend
    "React", "React Native", "Next.js", "Vue.js", "Vue", "Nuxt.js", "Angular", "Svelte", 
    "TypeScript", "JavaScript", "HTML5", "CSS3", "Tailwind CSS", "Bootstrap", "Redux",
    "Zustand", "Webpack", "Vite", "GraphQL", "REST API",
    # Backend
    "Python", "FastAPI", "Django", "Flask", "Node.js", "Express", "NestJS", "Go", "Golang",
    "Java", "Spring Boot", "C#", ".NET", "ASP.NET", "Ruby", "Ruby on Rails", "PHP", "Laravel",
    "Rust", "Scala", "C++", "Microservices",
    # Databases & Caching
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Supabase", "Firebase", "Elasticsearch",
    "DynamoDB", "Cassandra", "Prisma", "Drizzle", "SQLAlchemy", "Kafka", "RabbitMQ",
    # Cloud & DevOps
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Google Cloud", "CI/CD", "GitHub Actions",
    "Terraform", "Linux", "Nginx", "Serverless", "Vercel", "Render", "AWS Lambda",
    # AI / Data
    "Machine Learning", "Deep Learning", "Pandas", "NumPy", "PyTorch", "TensorFlow", "Scikit-Learn",
    "Playwright", "Selenium", "Scrapy", "BeautifulSoup", "LLM", "OpenAI", "Gemini", "LangChain",
    "NLP", "Data Engineering", "ETL", "Tableau", "PowerBI"
]

EXPERIENCE_KEYWORDS = {
    "Junior": ["junior", "entry", "intern", "internship", "graduate", "0-1 year", "0-2 years", "associate"],
    "Mid-Level": ["mid", "intermediate", "2-4 years", "2-5 years", "3+ years", "3-5 years"],
    "Senior": ["senior", "sr", "lead", "principal", "architect", "staff", "head of", "director", "5+ years", "7+ years", "10+ years"]
}

class AIJobHandler:
    def __init__(self, api_key: Optional[str] = None):
        # Read API key from parameter or environment
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    def extract_tech_stack_offline(self, text: str) -> List[str]:
        """High-speed regex based tech stack extractor."""
        if not text or not isinstance(text, str):
            return []
        
        found_skills: Set[str] = set()
        text_lower = f" {text.lower()} "

        for skill in COMMON_TECH_SKILLS:
            # Word boundary matching to prevent false positives (e.g. 'Go' in 'Good')
            escaped = re.escape(skill.lower())
            pattern = rf"(?:\b|\s){escaped}(?:\b|\s|[,\.\/\(\)])"
            if re.search(pattern, text_lower):
                found_skills.add(skill)

        return sorted(list(found_skills))

    def detect_experience_level_offline(self, title: str, requirements: str) -> str:
        """Determines experience level from title and requirements."""
        combined = f"{title} {requirements}".lower()

        for level, keywords in EXPERIENCE_KEYWORDS.items():
            for kw in keywords:
                if re.search(rf"\b{re.escape(kw)}\b", combined):
                    if level == "Senior" and any(j in title.lower() for j in ["junior", "intern"]):
                        continue
                    return level
        
        return "Mid-Level"  # Standard default

    def generate_heuristic_summary(self, title: str, company: str, skills: List[str], requirements: str) -> str:
        """Generates a clean 2-line role summary without external API calls."""
        skill_str = ", ".join(skills[:4]) if skills else "modern web technologies"
        comp = company if company and company != "N/A" else "the hiring team"
        
        line1 = f"Seeking a {title} at {comp} to build scalable solutions using {skill_str}."
        if requirements and len(requirements) > 20 and "click 'apply'" not in requirements.lower():
            # Clean snippet
            cleaned_req = re.sub(r'\s+', ' ', requirements).strip()
            if len(cleaned_req) > 120:
                cleaned_req = cleaned_req[:117] + "..."
            line2 = f"Key Focus: {cleaned_req}"
        else:
            line2 = "Key Focus: Delivering high-quality features, collaborating with cross-functional teams, and code optimization."
        
        return f"{line1}\n{line2}"

    def analyze_single_job_gemini(self, job: Dict[str, Any], custom_api_key: Optional[str] = None) -> Dict[str, Any]:
        """Calls Google Gemini API for deep summarization and structured extraction."""
        key = custom_api_key or self.api_key
        if not key:
            return self.analyze_single_job_offline(job)

        title = job.get("title", "")
        company = job.get("company", "")
        req = job.get("requirements", "")
        location = job.get("location", "")

        prompt = f"""
You are an expert technical recruiter and data analyst. Analyze this job listing:
- Title: {title}
- Company: {company}
- Location: {location}
- Requirements/Snippet: {req}

Provide a JSON response with the following exact keys:
{{
  "tech_stack": ["Skill1", "Skill2", ...],
  "experience_level": "Junior" or "Mid-Level" or "Senior",
  "ai_summary": "Two concise sentences describing the core role and key responsibilities."
}}
Return ONLY valid JSON with no markdown backticks or commentary.
"""
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "response_mime_type": "application/json"}
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            http_req = urllib.request.Request(
                endpoint,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(http_req, timeout=8) as response:
                if response.status == 200:
                    resp_json = json.loads(response.read().decode("utf-8"))
                    text_content = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(text_content.strip())
                    return {
                        "tech_stack": parsed.get("tech_stack", self.extract_tech_stack_offline(f"{title} {req}")),
                        "experience_level": parsed.get("experience_level", self.detect_experience_level_offline(title, req)),
                        "ai_summary": parsed.get("ai_summary", self.generate_heuristic_summary(title, company, [], req))
                    }
        except Exception as e:
            print(f"[!] Gemini API call failed, falling back to offline NLP: {e}")

        return self.analyze_single_job_offline(job)

    def analyze_single_job_offline(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Fast offline analysis for a single job."""
        title = job.get("title", "")
        company = job.get("company", "")
        req = job.get("requirements", "")

        combined_text = f"{title} {req}"
        skills = self.extract_tech_stack_offline(combined_text)
        exp_level = self.detect_experience_level_offline(title, req)
        summary = self.generate_heuristic_summary(title, company, skills, req)

        return {
            "tech_stack": skills,
            "experience_level": exp_level,
            "ai_summary": summary
        }

    def batch_enrich_jobs(self, jobs: List[Dict[str, Any]], custom_api_key: Optional[str] = None, max_gemini_calls: int = 5) -> List[Dict[str, Any]]:
        """
        Enriches a list of jobs with tech stack, experience level, and AI summaries.
        Uses Gemini API for the top priority jobs and fast offline NLP for the rest.
        """
        enriched_jobs = []
        key = custom_api_key or self.api_key

        for i, job in enumerate(jobs):
            job_copy = dict(job)
            
            # If user has an API key and within quota limit, use Gemini for first N jobs
            if key and i < max_gemini_calls:
                analysis = self.analyze_single_job_gemini(job_copy, custom_api_key=key)
            else:
                analysis = self.analyze_single_job_offline(job_copy)

            job_copy["tech_stack"] = analysis.get("tech_stack", [])
            job_copy["experience_level"] = analysis.get("experience_level", "Mid-Level")
            job_copy["ai_summary"] = analysis.get("ai_summary", "")

            enriched_jobs.append(job_copy)

        return enriched_jobs

    def calculate_match_score(self, job: Dict[str, Any], candidate_skills: List[str], resume_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates a candidate match score (0 - 100%) against a job.
        Returns score, matching skills, and missing in-demand skills.
        """
        # Collect candidate skills from list and resume text
        all_candidate_skills: Set[str] = {s.strip().lower() for s in candidate_skills if s.strip()}
        if resume_text:
            extracted_from_resume = self.extract_tech_stack_offline(resume_text)
            for s in extracted_from_resume:
                all_candidate_skills.add(s.lower())

        if not all_candidate_skills:
            return {
                "match_score": 0,
                "matched_skills": [],
                "missing_skills": job.get("tech_stack", [])
            }

        job_skills = job.get("tech_stack", [])
        if not job_skills:
            # Extract on the fly if missing
            job_skills = self.extract_tech_stack_offline(f"{job.get('title', '')} {job.get('requirements', '')}")

        job_skills_lower = {s.lower(): s for s in job_skills}
        title_lower = job.get("title", "").lower()

        matched: List[str] = []
        missing: List[str] = []

        for s_low, s_orig in job_skills_lower.items():
            if s_low in all_candidate_skills or any(s_low in cand or cand in s_low for cand in all_candidate_skills):
                matched.append(s_orig)
            else:
                missing.append(s_orig)

        # Base score calculation: Ratio of required skills matched
        if job_skills:
            skill_ratio = len(matched) / len(job_skills)
            base_score = skill_ratio * 80.0
        else:
            # If no specific tech skills listed in job, check title keyword overlap
            title_hits = sum(1 for cand in all_candidate_skills if cand in title_lower)
            base_score = min(70.0, title_hits * 35.0)

        # Title alignment bonus (up to 20 points)
        title_bonus = 0.0
        for cand in all_candidate_skills:
            if cand in title_lower:
                title_bonus += 10.0
        title_bonus = min(20.0, title_bonus)

        final_score = int(round(min(100.0, base_score + title_bonus)))

        return {
            "match_score": final_score,
            "matched_skills": matched,
            "missing_skills": missing
        }

    def generate_market_analytics(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Computes aggregate statistics for Chart.js dashboards:
        - Top Tech Stack Frequencies
        - Workplace Type breakdown (Remote vs Hybrid vs On-site)
        - Experience Level distribution
        """
        if not jobs:
            return {
                "total_jobs": 0,
                "top_skills": [],
                "workplace_distribution": {"Remote": 0, "On-site": 0, "Hybrid": 0},
                "experience_distribution": {"Junior": 0, "Mid-Level": 0, "Senior": 0},
                "remote_ratio": 0.0,
                "top_skill_name": "N/A"
            }

        skill_counts: Dict[str, int] = {}
        wp_counts: Dict[str, int] = {"Remote": 0, "On-site": 0, "Hybrid": 0}
        exp_counts: Dict[str, int] = {"Junior": 0, "Mid-Level": 0, "Senior": 0}

        for job in jobs:
            # Skills tally
            skills = job.get("tech_stack")
            if not skills:
                skills = self.extract_tech_stack_offline(f"{job.get('title', '')} {job.get('requirements', '')}")
            
            for s in skills:
                skill_counts[s] = skill_counts.get(s, 0) + 1

            # Workplace tally
            wp = str(job.get("workplace_type", "")).lower()
            loc = str(job.get("location", "")).lower()
            title = str(job.get("title", "")).lower()

            if "remote" in wp or "remote" in loc or "remote" in title:
                wp_counts["Remote"] += 1
            elif "hybrid" in wp or "hybrid" in loc or "hybrid" in title:
                wp_counts["Hybrid"] += 1
            else:
                wp_counts["On-site"] += 1

            # Experience level tally
            exp = job.get("experience_level")
            if not exp or exp not in exp_counts:
                exp = self.detect_experience_level_offline(job.get("title", ""), job.get("requirements", ""))
            exp_counts[exp] = exp_counts.get(exp, 0) + 1

        # Sort top 10 skills
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_skills_formatted = [{"name": name, "count": count} for name, count in sorted_skills]

        total = len(jobs)
        remote_ratio = round((wp_counts["Remote"] / total) * 100, 1) if total > 0 else 0.0
        top_skill_name = sorted_skills[0][0] if sorted_skills else "N/A"

        return {
            "total_jobs": total,
            "top_skills": top_skills_formatted,
            "workplace_distribution": wp_counts,
            "experience_distribution": exp_counts,
            "remote_ratio": remote_ratio,
            "top_skill_name": top_skill_name
        }
