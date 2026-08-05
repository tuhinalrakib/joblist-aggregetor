"""
Data Handler Module (data_handler.py)
------------------------------------
Handles cleaning, filtering, deduplicating, and saving scraped job listings to:
- CSV
- JSON
- Interactive HTML Dashboard
- PDF Report (via Playwright rendering)
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import pandas as pd
from playwright.sync_api import sync_playwright

import re

def parse_relative_hours(date_str: Any) -> float:
    if not date_str or not isinstance(date_str, str):
        return 999999.0
    s = date_str.lower().strip()
    if any(k in s for k in ["just now", "recently", "moment", "second"]):
        return 0.0
    match = re.search(r"(\d+)\s*(minute|min|hour|hr|day|week|month|year)", s)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        if unit.startswith("min"):
            return val / 60.0
        elif unit.startswith("hour") or unit.startswith("hr"):
            return float(val)
        elif unit.startswith("day"):
            return val * 24.0
        elif unit.startswith("week"):
            return val * 24.0 * 7.0
        elif unit.startswith("month"):
            return val * 24.0 * 30.0
        elif unit.startswith("year"):
            return val * 24.0 * 365.0
    if "hour" in s or "hr" in s:
        return 1.0
    if "day" in s:
        return 24.0
    if "week" in s:
        return 168.0
    if "month" in s:
        return 720.0
    if "year" in s:
        return 8760.0
    return 999999.0

class JobDataHandler:
    def __init__(self, raw_jobs: List[Dict[str, Any]]):
        self.raw_jobs = raw_jobs
        self.df = pd.DataFrame(raw_jobs) if raw_jobs else pd.DataFrame()

    def clean_data(self, experience_level: Optional[str] = "all") -> pd.DataFrame:
        """Clean raw scraped data: remove empty rows, strip whitespace, deduplicate, and filter experience mismatches."""
        if self.df.empty:
            print("[!] No job listings found to clean.")
            return self.df

        # Strip whitespace from string columns
        for col in self.df.columns:
            if self.df[col].dtype == "object":
                self.df[col] = self.df[col].astype(str).str.strip()

        # Deduplicate based on job link or combination of title and company
        initial_count = len(self.df)
        if "link" in self.df.columns:
            self.df.drop_duplicates(subset=["link"], keep="first", inplace=True)
        elif "title" in self.df.columns and "company" in self.df.columns:
            self.df.drop_duplicates(subset=["title", "company"], keep="first", inplace=True)

        deduped_count = len(self.df)
        if initial_count != deduped_count:
            print(f"[+] Removed {initial_count - deduped_count} duplicate job listings.")

        # Experience level strict filtering by job title
        exp_str = str(experience_level).lower().strip() if experience_level else "all"
        if exp_str in ["entry", "internship", "associate", "1", "2", "3"]:
            if "title" in self.df.columns:
                senior_pattern = r"\b(senior|sr|lead|staff|principal|architect|manager|director|head|vp)\b"
                mask = self.df["title"].astype(str).str.lower().str.contains(senior_pattern, regex=True)
                filtered_out = mask.sum()
                if filtered_out > 0:
                    print(f"[+] Strict Filter: Removed {filtered_out} Senior/Lead job titles for Entry-Level selection.")
                    self.df = self.df[~mask]

        # Sort by relative date (most recent first)
        if "date_posted" in self.df.columns:
            self.df["_sort_hours"] = self.df["date_posted"].apply(parse_relative_hours)
            self.df.sort_values(by="_sort_hours", ascending=True, inplace=True)
            self.df.drop(columns=["_sort_hours"], inplace=True)

        return self.df

    def save_to_csv(self, output_file: str = "jobs_output.csv") -> Path:
        """Save cleaned data to CSV."""
        cleaned_df = self.clean_data()
        out_path = Path(output_file)
        cleaned_df.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"[✔] Saved {len(cleaned_df)} job listings to CSV: {out_path.resolve()}")
        return out_path

    def save_to_json(self, output_file: str = "jobs_output.json") -> Path:
        """Save cleaned data to JSON."""
        cleaned_df = self.clean_data()
        out_path = Path(output_file)
        cleaned_df.to_json(out_path, orient="records", indent=4, force_ascii=False)
        print(f"[✔] Saved {len(cleaned_df)} job listings to JSON: {out_path.resolve()}")
        return out_path

    def save_to_html(self, output_file: str = "jobs_report.html") -> Path:
        """Generate a sleek, interactive HTML report with search and clickable apply links."""
        cleaned_df = self.clean_data()
        jobs_list = cleaned_df.to_dict(orient="records")
        out_path = Path(output_file)

        jobs_json_str = json.dumps(jobs_list, ensure_ascii=False)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Listing Aggregator Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: #1e293b;
            --accent: #38bdf8;
            --accent-hover: #0284c7;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --badge-bg: #0284c720;
            --badge-text: #38bdf8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }}
        body {{ background-color: var(--bg); color: var(--text-main); padding: 30px 20px; line-height: 1.5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border-bottom: 1px solid var(--border); padding-bottom: 15px; }}
        h1 {{ font-size: 1.8rem; font-weight: 700; color: var(--accent); }}
        .badge-count {{ background: var(--badge-bg); color: var(--badge-text); padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 0.9rem; }}
        .search-bar {{ width: 100%; padding: 14px 18px; font-size: 1rem; border-radius: 10px; border: 1px solid var(--border); background: var(--card-bg); color: var(--text-main); margin-bottom: 25px; outline: none; }}
        .search-bar:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2); }}
        .table-container {{ overflow-x: auto; background: var(--card-bg); border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3); }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 0.95rem; }}
        th {{ background: #090d16; padding: 16px 20px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 0.05em; border-bottom: 1px solid var(--border); }}
        td {{ padding: 16px 20px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover {{ background: rgba(255, 255, 255, 0.02); }}
        .job-title {{ font-weight: 600; font-size: 1.05rem; color: #ffffff; margin-bottom: 4px; }}
        .company-name {{ color: var(--text-muted); font-size: 0.88rem; display: flex; align-items: center; gap: 6px; }}
        .location-badge {{ display: inline-block; background: rgba(56, 189, 248, 0.1); color: var(--accent); padding: 4px 10px; border-radius: 6px; font-size: 0.82rem; font-weight: 500; }}
        .apply-btn {{ display: inline-block; background: var(--accent); color: #090d16; text-decoration: none; padding: 8px 16px; border-radius: 8px; font-weight: 600; font-size: 0.88rem; transition: all 0.2s ease; }}
        .apply-btn:hover {{ background: var(--accent-hover); color: #ffffff; transform: translateY(-1px); }}
        .print-btn {{ background: transparent; border: 1px solid var(--border); color: var(--text-main); padding: 8px 16px; border-radius: 8px; cursor: pointer; font-weight: 500; transition: 0.2s; }}
        .print-btn:hover {{ background: var(--card-bg); border-color: var(--accent); }}
        @media (max-width: 768px) {{
            body {{ padding: 16px 12px; }}
            header {{ flex-direction: column; align-items: flex-start; gap: 12px; }}
            .table-container {{ background: transparent; border: none; box-shadow: none; overflow: visible; }}
            table, thead, tbody, th, td, tr {{ display: block; width: 100%; }}
            thead tr {{ position: absolute; top: -9999px; left: -9999px; }}
            tbody tr {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 14px; padding: 14px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }}
            td {{ border: none; padding: 6px 0; }}
            .apply-btn {{ display: block; width: 100%; text-align: center; padding: 10px; margin-top: 8px; }}
        }}
        @media print {{
            body {{ background: #ffffff; color: #000000; padding: 0; }}
            .search-bar, .print-btn {{ display: none; }}
            .table-container {{ box-shadow: none; border: 1px solid #ccc; }}
            th {{ background: #f1f5f9; color: #000000; }}
            td {{ border-bottom: 1px solid #e2e8f0; color: #000000; }}
            .job-title {{ color: #000000; }}
            .apply-btn {{ background: #0284c7; color: #ffffff; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>🎯 Job Listing Aggregator</h1>
                <p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 4px;">Aggregated Job Results Report</p>
            </div>
            <div style="display: flex; gap: 12px; align-items: center;">
                <span class="badge-count" id="job-count">{len(jobs_list)} Jobs Found</span>
                <button class="print-btn" onclick="window.print()">🖨️ Export PDF / Print</button>
            </div>
        </header>

        <div style="display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; align-items: center;">
            <input type="text" class="search-bar" id="search-input" style="flex: 1; margin-bottom: 0;" placeholder="🔍 Search by job title, company, or location..." onkeyup="applyFilterAndSort()">
            
            <div style="display: flex; align-items: center; gap: 8px;">
                <label for="sort-select" style="font-weight: 600; font-size: 0.88rem; color: var(--text-muted); white-space: nowrap;">Sort By:</label>
                <select id="sort-select" onchange="applyFilterAndSort()" style="padding: 12px 16px; border-radius: 10px; background: var(--card-bg); color: var(--text-main); border: 1px solid var(--border); font-size: 0.95rem; cursor: pointer; outline: none;">
                    <option value="newest" selected>⏱️ Most Recent First (Default)</option>
                    <option value="title_asc">🔤 Job Title (A → Z)</option>
                    <option value="title_desc">🔤 Job Title (Z → A)</option>
                    <option value="company_asc">🏢 Company Name (A → Z)</option>
                    <option value="location_asc">📍 Location (A → Z)</option>
                </select>
            </div>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr style="user-select: none;">
                        <th style="width: 32%; cursor: pointer;" onclick="toggleSortHeader('title')">Job Title & Company ↕</th>
                        <th style="width: 18%; cursor: pointer;" onclick="toggleSortHeader('location')">Location ↕</th>
                        <th style="width: 15%; cursor: pointer;" onclick="toggleSortHeader('date')">Date Posted ↕</th>
                        <th style="width: 23%;">Requirements</th>
                        <th style="width: 12%; text-align: center;">Action</th>
                    </tr>
                </thead>
                <tbody id="job-table-body">
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const rawJobs = {jobs_json_str};

        function renderJobs(data) {{
            const tbody = document.getElementById("job-table-body");
            tbody.innerHTML = "";
            document.getElementById("job-count").innerText = `${{data.length}} Jobs Found`;

            if (data.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 40px; color: var(--text-muted);">No job listings match your search.</td></tr>`;
                return;
            }}

            data.forEach(job => {{
                const tr = document.createElement("tr");
                
                const titleCompany = `
                    <div>
                        <div class="job-title">${{escapeHtml(job.title || 'N/A')}}</div>
                        <div class="company-name">🏢 ${{escapeHtml(job.company || 'N/A')}}</div>
                    </div>
                `;

                const location = `
                    <span class="location-badge">📍 ${{escapeHtml(job.location || 'Remote')}}</span>
                `;

                const dateBadge = `<span style="display:inline-block; background:rgba(56, 189, 248, 0.1); color:var(--accent); padding:4px 10px; border-radius:6px; font-size:0.82rem; font-weight:600;">🕒 ${{escapeHtml(job.date_posted || 'Recently')}}</span>`;

                const reqs = `
                    <div style="color: var(--text-muted); font-size: 0.88rem; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        ${{escapeHtml(job.requirements || 'N/A')}}
                    </div>
                `;

                const applyBtn = job.link && job.link !== 'N/A' 
                    ? `<a href="${{job.link}}" target="_blank" class="apply-btn">Apply Now ↗</a>` 
                    : `<span style="color: var(--text-muted);">N/A</span>`;

                tr.innerHTML = `
                    <td>${{titleCompany}}</td>
                    <td>${{location}}</td>
                    <td>${{dateBadge}}</td>
                    <td>${{reqs}}</td>
                    <td style="text-align: center;">${{applyBtn}}</td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        function toggleSortHeader(field) {{
            const selectElem = document.getElementById("sort-select");
            if (field === 'title') {{
                selectElem.value = (selectElem.value === 'title_asc') ? 'title_desc' : 'title_asc';
            }} else if (field === 'location') {{
                selectElem.value = 'location_asc';
            }} else if (field === 'date') {{
                selectElem.value = 'newest';
            }}
            applyFilterAndSort();
        }}

        function applyFilterAndSort() {{
            const query = document.getElementById("search-input").value.toLowerCase();
            const sortOption = document.getElementById("sort-select").value;

            let filtered = rawJobs.filter(j => 
                (j.title && j.title.toLowerCase().includes(query)) ||
                (j.company && j.company.toLowerCase().includes(query)) ||
                (j.location && j.location.toLowerCase().includes(query)) ||
                (j.date_posted && j.date_posted.toLowerCase().includes(query))
            );

            if (sortOption === "title_asc") {{
                filtered.sort((a, b) => (a.title || "").localeCompare(b.title || ""));
            }} else if (sortOption === "title_desc") {{
                filtered.sort((a, b) => (b.title || "").localeCompare(a.title || ""));
            }} else if (sortOption === "company_asc") {{
                filtered.sort((a, b) => (a.company || "").localeCompare(b.company || ""));
            }} else if (sortOption === "location_asc") {{
                filtered.sort((a, b) => (a.location || "").localeCompare(b.location || ""));
            }}

            renderJobs(filtered);
        }}

        function escapeHtml(str) {{
            return String(str)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;");
        }}

        // Initial render
        applyFilterAndSort();
    </script>
</body>
</html>
"""
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[✔] Generated interactive HTML report: {out_path.resolve()}")
        return out_path

    def save_to_pdf(self, pdf_file: str = "jobs_report.pdf", html_file: str = "jobs_report.html") -> Path:
        """Render the HTML report into a beautiful PDF using Playwright."""
        html_path = self.save_to_html(html_file)
        pdf_path = Path(pdf_file)

        print(f"[+] Rendering PDF report via Playwright...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(html_path.resolve().as_uri())
            page.wait_for_selector("table")

            # Render A4 PDF
            page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                margin={"top": "15mm", "bottom": "15mm", "left": "10mm", "right": "10mm"}
            )
            browser.close()

        print(f"[✔] Successfully generated PDF document: {pdf_path.resolve()}")
        return pdf_path
