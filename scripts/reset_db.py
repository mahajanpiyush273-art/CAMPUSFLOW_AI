"""
CampusFlow AI - Database Reset Utility
Safely re-initializes all SQLite tables and restores clean seed data.
Usage: python scripts/reset_db.py
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import init_db
from backend.seed import seed_database


def reset_database():
    print("Resetting CampusFlow AI SQLite database...")
    init_db()
    seed_database(force=True)
    print("Database reset and re-seeded successfully.")
    print("Demo accounts ready:")
    print("  Student: student1 / student123 (Aarav Sharma)")
    print("  Student: student2 / student123 (Priya Patel)")
    print("  Admin:   admin1 / admin123 (Admin Office Staff)")


if __name__ == "__main__":
    reset_database()
