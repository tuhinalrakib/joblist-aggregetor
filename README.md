# ⚡ JobFlow - Intelligent Job Aggregator & Market Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-Automated-2EAD33.svg)](https://playwright.dev/python/)
[![Chart.js](https://img.shields.io/badge/Chart.js-Analytics-FF6384.svg)](https://www.chartjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An end-to-end, containerized **Web Scraping & Market Intelligence Platform** built with **Python**, **FastAPI**, **Playwright**, and **Chart.js**.

The platform automatically scrapes dynamic job postings across portals, enriches listings with **Key Tech Stack tags**, classifies **Experience Levels**, calculates **Candidate Resume/Skills Match Scores (0-100%)**, and visualizes **Tech Demand Market Insights** via interactive Chart.js dashboards.

---

## ✨ Key Features

- 🕷️ **Dual-Engine Scraping Automation**: Concurrent headless browser scraping via Playwright with smart fallback to high-speed BeautifulSoup for serverless environments.
- 🏷️ **Tech Stack & Experience Extraction**:
  - Automatically extracts key tech stack tags (`React`, `Python`, `FastAPI`, `Docker`, `PostgreSQL`, etc.).
  - Classifies experience levels (`Junior`, `Mid-Level`, `Senior`).
- 🎯 **"Match My Resume / Skills" Engine**:
  - Interactive skill selector and resume text analyzer.
  - Computes real-time **Match Scores (%)** and highlights matching vs missing skills.
  - One-click sorting by Highest Match.
- 📊 **Interactive Market Analytics & Insights (Chart.js)**:
  - Top 10 In-Demand Technologies bar chart.
  - Remote vs Hybrid vs On-site workplace distribution doughnut chart.
  - Real-time KPI metrics (Total Jobs, Remote Ratio, Top Skill, Avg Match Score).
- 🧹 **Pandas Data Cleaning Pipeline**: Automated deduplication, whitespace stripping, and strict title/experience filtering.
- 📄 **Multi-Format Export**: 1-click downloads in **CSV**, **JSON**, **HTML**, and **PDF** formats.
- 🐳 **Dockerized & Cloud Ready**: Fully containerized and optimized for 1-click deployment on **Render** or **Vercel**.

---

## 🛠️ Tech Stack

| Domain | Technology |
| :--- | :--- |
| **Backend API** | [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/) |
| **Scraping Engine** | [Playwright Python](https://playwright.dev/python/) & [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) |
| **Taxonomy & Extraction** | Python Regex Engine & Taxonomy Classifier |
| **Data Processing** | [Pandas](https://pandas.pydata.org/) |
| **Frontend UI & Visuals** | HTML5, CSS3 Glassmorphism, Vanilla JS & [Chart.js](https://www.chartjs.org/) |
| **Containerization** | [Docker](https://www.docker.com/) |
| **Deployment** | [Render](https://render.com/) & [Vercel](https://vercel.com/) |

---

## 📂 Project Structure

```text
├── app.py                 # FastAPI backend application & REST API endpoints
├── analytics_handler.py   # Tech extractor, experience classifier & skills matcher
├── scraper.py             # Dual-engine Playwright & BS4 web scraper
├── data_handler.py        # Data cleaning, transformation & file exports
├── templates/
│   └── index.html         # Interactive glassmorphism dashboard with Chart.js
├── auth.json              # Saved browser session state (optional)
├── Dockerfile             # Docker container definition
├── render.yaml            # Render Cloud Blueprint deployment file
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Local Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/joblist-aggregator.git
   cd joblist-aggregator
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # On Windows
   python -m venv job_env
   job_env\Scripts\activate

   # On macOS/Linux
   python -m venv job_env
   source job_env/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

5. **Run the server:**
   ```bash
   uvicorn app:app --reload --port 8000
   ```

6. **Open in browser:**
   Navigate to `http://localhost:8000` to access the JobFlow Dashboard.

---

## 🐳 Running with Docker

1. **Build the Docker image:**
   ```bash
   docker build -t jobflow .
   ```

2. **Run the Docker container:**
   ```bash
   docker run -d -p 8000:8000 --name jobflow-container jobflow
   ```

3. **Access the application:**
   Visit `http://localhost:8000` in your web browser.

---

## 📡 API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Serves the interactive Web Dashboard |
| `/api/scrape` | `POST` | Triggers scraping job with payload `{ keyword, location, max_pages }` |
| `/api/match` | `POST` | Calculates candidate match score (%) based on skills / resume |
| `/api/analytics` | `POST` | Generates aggregated tech demand and workplace statistics |
| `/api/download/csv` | `GET` | Downloads scraped jobs as `scraped_jobs.csv` |
| `/api/download/json` | `GET` | Downloads scraped jobs as `scraped_jobs.json` |
| `/api/download/pdf` | `GET` | Downloads scraped jobs as `scraped_jobs.pdf` |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
