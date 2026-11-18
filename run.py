"""
CampusFlow AI - Single-Command Application Launcher
Starts the FastAPI server with Uvicorn, verifies environment setup,
seeds database if required, and opens the application in your default browser.

Usage:
    python run.py
"""

import os
from pathlib import Path
import shutil
import sys
import threading
import time
import webbrowser

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def check_environment():
    """Verify virtual environment, .env file, and required dependencies."""
    print("Checking system environment...")

    # 1. Check Python version
    if sys.version_info < (3, 10):
        print(f"ERROR: Python 3.10 or higher is required. Found Python {sys.version.split()[0]}")
        sys.exit(1)

    # 2. Check .env file
    env_file = BASE_DIR / ".env"
    env_example = BASE_DIR / ".env.example"
    if not env_file.exists():
        if env_example.exists():
            print("Creating .env from .env.example...")
            shutil.copy(env_example, env_file)
        else:
            print("Creating default .env...")
            env_file.write_text("SECRET_KEY=campusflow-secret-key-production-32chars\n", encoding="utf-8")

    # 3. Check database initialization
    from backend.database import init_db
    from backend.seed import seed_database
    init_db()
    seed_database(force=False)


def open_browser(url: str, delay: float = 1.5):
    """Open default browser after a brief delay to allow server startup."""
    def _open():
        time.sleep(delay)
        print(f"\nOpening {url} in your default browser...")
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open, daemon=True).start()


def print_banner():
    """Display startup banner and access instructions."""
    banner = r"""
  ========================================================================
     ___                            _____ _                 _    ___ 
    / __\__ _ _ __ ___  _ __  _   _/ ____| | _____      __ / \  |_ _|
   / /  / _` | '_ ` _ \| '_ \| | | \___ \| |/ _ \ \ /\ / // _ \  | | 
  / /__| (_| | | | | | | |_) | |_| |___) | | (_) \ V  V // ___ \ | | 
  \____/\__,_|_| |_| |_| .__/ \__,_|_____/|_|\___/ \_/\_//_/   \_|___|
                       |_|   Ask. Verify. Act. — CampusFlow AI        
  ========================================================================
    * Problem: Smart Campus Query & Action Assistant (Aarambhathon)
    * Core: Answers only from verified notices with grounded confidence.
    * Server running at: http://127.0.0.1:8000
  ========================================================================
    DEMO LOGIN CREDENTIALS:
    ----------------------------------------------------------------------
    Role       Username    Password    Account Name
    ----------------------------------------------------------------------
    Student    student1    student123  Aarav Sharma (Full Profile)
    Student    student2    student123  Priya Patel (Partial Profile)
    Admin      admin1      admin123    Admin Office Staff (Full Access)
    ----------------------------------------------------------------------
    Press Ctrl + C in this terminal to stop the server.
  ========================================================================
    """
    print(banner)


def main():
    check_environment()
    print_banner()

    # Open browser on login page
    open_browser("http://127.0.0.1:8000/login", delay=1.2)

    import uvicorn
    # Start uvicorn server
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
