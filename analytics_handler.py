"""
Job Analytics & Skills Handler (analytics_handler.py)
-----------------------------------------------------
Handles deterministic, non-AI operations:
1. Tech Stack Taxonomy & Regex-based Extraction
2. Experience Level Detection
3. Candidate Skills Matcher (Score 0-100%)
4. Market Intelligence & Tech Demand Aggregation (Chart.js)
"""

import re
from typing import List, Dict, Any, Optional, Set

# Comprehensive Tech Stack Taxonomy for High-Precision Keyword Extraction
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
    # Data & Automation
    "Pandas", "NumPy", "PyTorch", "TensorFlow", "Scikit-Learn",
    "Playwright", "Selenium", "Scrapy", "BeautifulSoup", "Data Engineering", "ETL", "Tableau", "PowerBI"
]

EXPERIENCE_KEYWORDS = {
    "Junior": [
        "junior", "entry", "entry-level", "entry level", "intern", "internship",
        "graduate", "fresher", "trainee", "associate", "early career", "new grad",
        "0-1 year", "0-2 years", "1-2 years", "0 to 1 year", "0 to 2 years",
        "0-1", "0-2", "1-2", "junior software", "junior developer", "junior engineer"
    ],
    "Senior": [
        "senior", "sr", "sr.", "lead", "principal", "architect", "staff",
        "head of", "director", "manager", "vp", "5+ years", "6+ years",
        "7+ years", "8+ years", "10+ years"
    ],
    "Mid-Level": [
        "mid", "mid-level", "intermediate", "2-4 years", "2-5 years", "3+ years", "3-5 years", "4+ years"
    ]
}

class AnalyticsHandler:
    def __init__(self):
        pass

    def extract_tech_stack(self, text: str) -> List[str]:
        """High-speed regex based tech stack extractor."""
        if not text or not isinstance(text, str):
            return []
        
        found_skills: Set[str] = set()
        text_lower = f" {text.lower()} "

        for skill in COMMON_TECH_SKILLS:
            escaped = re.escape(skill.lower())
            pattern = rf"(?:\b|\s){escaped}(?:\b|\s|[,\.\/\(\)])"
            if re.search(pattern, text_lower):
                found_skills.add(skill)

        return sorted(list(found_skills))

    def detect_experience_level(self, title: str, requirements: str, requested_level: Optional[str] = None) -> str:
        """Determines experience level from job title, requirements, and requested search context."""
        combined = f"{title} {requirements}".lower()
        title_lower = title.lower()

        # 1. Direct keyword check
        for kw in EXPERIENCE_KEYWORDS["Junior"]:
            if re.search(rf"\b{re.escape(kw)}\b", combined):
                return "Junior"

        for kw in EXPERIENCE_KEYWORDS["Senior"]:
            if re.search(rf"\b{re.escape(kw)}\b", combined):
                if not any(j in title_lower for j in ["junior", "intern", "assistant"]):
                    return "Senior"

        for kw in EXPERIENCE_KEYWORDS["Mid-Level"]:
            if re.search(rf"\b{re.escape(kw)}\b", combined):
                return "Mid-Level"

        # 2. If no explicit keywords found in text, infer from user's search filter
        if requested_level:
            req_l = str(requested_level).lower().strip()
            if req_l in ["entry", "internship", "associate", "junior", "1", "2", "3"]:
                return "Junior"
            elif req_l in ["mid_senior", "mid", "4"]:
                return "Mid-Level"
            elif req_l in ["director", "executive", "senior", "5", "6"]:
                return "Senior"

        return "Mid-Level"

    def calculate_match_score(self, job: Dict[str, Any], candidate_skills: List[str], resume_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates a candidate skills match score (0 - 100%) against a job listing.
        Returns match score, matched skills list, and missing skills list.
        """
        all_candidate_skills: Set[str] = {s.strip().lower() for s in candidate_skills if s.strip()}
        if resume_text:
            extracted_from_resume = self.extract_tech_stack(resume_text)
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
            job_skills = self.extract_tech_stack(f"{job.get('title', '')} {job.get('requirements', '')}")

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
            skills = job.get("tech_stack")
            if not skills:
                skills = self.extract_tech_stack(f"{job.get('title', '')} {job.get('requirements', '')}")
            
            for s in skills:
                skill_counts[s] = skill_counts.get(s, 0) + 1

            wp = str(job.get("workplace_type", "")).lower()
            loc = str(job.get("location", "")).lower()
            title = str(job.get("title", "")).lower()

            if "remote" in wp or "remote" in loc or "remote" in title:
                wp_counts["Remote"] += 1
            elif "hybrid" in wp or "hybrid" in loc or "hybrid" in title:
                wp_counts["Hybrid"] += 1
            else:
                wp_counts["On-site"] += 1

            exp = job.get("experience_level")
            if not exp or exp not in exp_counts:
                exp = self.detect_experience_level(job.get("title", ""), job.get("requirements", ""))
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
