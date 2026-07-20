"""
CSV to HTML & PDF Converter Utility
-----------------------------------
Converts existing CSV job files (e.g., react_jobs.csv) into a beautiful HTML dashboard and PDF document.
"""

import sys
import pandas as pd
from pathlib import Path
from data_handler import JobDataHandler

def convert_csv(csv_path_str: str = "react_jobs.csv"):
    csv_path = Path(csv_path_str)
    if not csv_path.exists():
        print(f"[!] File {csv_path} not found.")
        return

    print(f"[+] Reading CSV data from: {csv_path.resolve()}")
    df = pd.read_csv(csv_path)
    
    # Filter out header/invalid rows if present
    jobs = df.to_dict(orient="records")
    
    handler = JobDataHandler(jobs)
    
    html_out = csv_path.with_suffix(".html")
    pdf_out = csv_path.with_suffix(".pdf")

    print(f"[+] Generating interactive HTML dashboard...")
    handler.save_to_html(str(html_out))

    print(f"[+] Generating PDF report...")
    handler.save_to_pdf(str(pdf_out), str(html_out))

    print(f"\n[✔] Conversion Successful!")
    print(f"    - HTML Dashboard: {html_out.resolve()}")
    print(f"    - PDF Report:    {pdf_out.resolve()}")

if __name__ == "__main__":
    file_input = sys.argv[1] if len(sys.argv) > 1 else "react_jobs.csv"
    convert_csv(file_input)
