#!/usr/bin/env python3
"""
Script to create the initial admin user.
Run from the backend/ directory: python scripts/create_admin.py
"""
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from getpass import getpass
from app.database import SessionLocal, engine, Base
from app.services.auth_service import auth_service
from app.models import User


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("=== Expense Tracker - Create Admin User ===\n")
    username = input("Username (3-50 chars, alphanumeric/_): ").strip()
    email = input("Email: ").strip()
    password = getpass("Password (min 8 chars, must include upper/lower/digit): ")
    confirm = getpass("Confirm password: ")

    if password != confirm:
        print("Passwords do not match. Exiting.")
        sys.exit(1)

    try:
        user = auth_service.register_user(db, username, email, password)
        print(f"\nUser '{username}' created successfully (ID: {user.id}).")
        print("Next step: Log in and complete 2FA enrollment via the web app.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
