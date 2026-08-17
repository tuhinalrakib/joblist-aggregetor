"""
Vercel Serverless Function Entry Point (api/index.py)
-----------------------------------------------------
Exposes the FastAPI application instance for Vercel's Python runtime.
"""

import sys
from pathlib import Path

# Add project root directory to sys.path so app.py and other modules are importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app
