"""
Session Saver Script (save_session.py)
---------------------------------------
This script opens a visible browser window allowing you to log in manually
to a target site (e.g. LinkedIn, Indeed, Glassdoor).
Once logged in, pressing Enter in the terminal will save your cookies and session state
to 'auth.json'. Subsequent scraping runs will re-use this session without needing password entry.
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

AUTH_FILE = Path(__file__).parent / "auth.json"

def save_user_session(target_url: str = "https://www.linkedin.com/login"):
    print(f"[+] Launching browser to save authentication state...")
    print(f"[+] Target Login URL: {target_url}")

    with sync_playwright() as p:
        # Launch non-headless browser so user can manually perform login / CAPTCHA
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(target_url)
        print("\n" + "=" * 60)
        print("ACTION REQUIRED:")
        print("1. Log in manually in the opened browser window.")
        print("2. Complete any 2FA or CAPTCHA verification if required.")
        print("3. Once logged in, return here and press Enter to save your session.")
        print("=" * 60 + "\n")

        input("Press Enter AFTER you have successfully logged in: ")

        # Save cookies & storage state
        context.storage_state(path=str(AUTH_FILE))
        print(f"[✔] Session successfully saved to: {AUTH_FILE.resolve()}")

        browser.close()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.linkedin.com/login"
    save_user_session(url)
