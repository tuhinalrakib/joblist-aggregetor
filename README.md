# 🔍 Automated Job Listing Aggregator & Scraper

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-Automated-2EAD33.svg)](https://playwright.dev/python/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An end-to-end, containerized **Web Scraping & Data Aggregation** application built with **Python**, **FastAPI**, and **Playwright**. The platform automatically scrapes job postings across portals based on custom keywords and locations, cleans raw data via an automated Pandas pipeline, and provides interactive downloads in **CSV, JSON, HTML, and PDF** formats via a modern web dashboard.

---

## ✨ Features

- 🕷️ **Automated Web Scraping Engine**: Headless browser automation using Playwright with support for session state persistence (`auth.json`).
- 🧹 **Data Cleaning Pipeline**: Automated data normalization, deduplication, and cleaning powered by Pandas & BeautifulSoup.
- 📄 **Multi-Format Export**: Generates exportable reports instantly in **CSV**, **JSON**, **HTML**, and **PDF** formats.
- ⚡ **Interactive Web Dashboard**: Built with FastAPI for triggering live scraping jobs and viewing results directly from the browser.
- 🐳 **Dockerized & Cloud Ready**: Fully containerized using official Playwright Docker images, optimized for 1-click deployment on **Render**.

---

## 🛠️ Tech Stack

| Domain | Technology |
| :--- | :--- |
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/) |
| **Browser Automation** | [Playwright Python](https://playwright.dev/python/) |
| **Data Processing** | [Pandas](https://pandas.pydata.org/) & [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) |
| **Templating & PDF** | [Jinja2](https://jinja.palletsprojects.com/) |
| **Containerization** | [Docker](https://www.docker.com/) |
| **Cloud Hosting** | [Render](https://render.com/) |

---

## 📂 Project Structure

```text
├── app.py                 # FastAPI backend application & API routes
├── scraper.py             # Playwright web scraping engine
├── data_handler.py        # Data cleaning, transformation & file exports
├── templates/
│   └── index.html         # Web dashboard UI
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

5. **Run the application:**
   ```bash
   uvicorn app:app --reload --port 8000
   ```

6. **Open in browser:**
   Navigate to `http://localhost:8000` to access the Web Dashboard.

---

## 🐳 Running with Docker

1. **Build the Docker image:**
   ```bash
   docker build -t joblist-aggregator .
   ```

2. **Run the Docker container:**
   ```bash
   docker run -d -p 8000:8000 --name job-scraper joblist-aggregator
   ```

3. **Access the application:**
   Visit `http://localhost:8000` in your web browser.

---

## ☁️ Deployment on Render

This project includes a pre-configured `render.yaml` blueprint for 1-click deployment on Render:

1. Push your code to GitHub.
2. Sign in to [Render](https://render.com).
3. Create a **New Web Service** and select **Docker** as the environment.
4. Render will automatically build the image using `Dockerfile` and start the server.

---

## 📡 API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Serves the web dashboard UI |
| `/api/scrape` | `POST` | Triggers scraping job with payload `{ keyword, location, max_pages }` |
| `/api/download/csv` | `GET` | Downloads scraped jobs as `scraped_jobs.csv` |
| `/api/download/json` | `GET` | Downloads scraped jobs as `scraped_jobs.json` |
| `/api/download/pdf` | `GET` | Downloads scraped jobs as `scraped_jobs.pdf` |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
