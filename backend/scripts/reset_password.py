#!/usr/bin/env python3
"""
Script to reset a user's password.
Run from the backend/ directory: python scripts/reset_password.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from getpass import getpass
from app.database import SessionLocal
from app.models.user import User
from app.services.auth_service import auth_service


def main():
    db = SessionLocal()

    print("=== Reset Password ===\n")
    username = input("Username: ").strip()

    user = db.query(User).filter(User.username == username).first()
    if not user:
        print(f"No user found with username '{username}'")
        db.close()
        sys.exit(1)

    print(f"Found user: {user.username} ({user.email})")
    new_password = getpass("New password (min 8 chars, upper+lower+digit): ")
    confirm = getpass("Confirm password: ")

    if new_password != confirm:
        print("Passwords do not match.")
        db.close()
        sys.exit(1)

    user.password_hash = auth_service.hash_password(new_password)
    db.commit()
    print(f"\nPassword reset successfully for '{username}'.")
    db.close()


if __name__ == "__main__":
    main()
