"""Provision a human-review operator without storing a plaintext password."""
from __future__ import annotations

import argparse
import getpass
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.auth import hash_password  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.db.enums import UserRole  # noqa: E402
from app.db.models import User  # noqa: E402


ALLOWED_OPERATOR_ROLES = {
    UserRole.EMERGENCY_COORDINATOR.value,
    UserRole.ADMINISTRATOR.value,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=sorted(ALLOWED_OPERATOR_ROLES), required=True)
    args = parser.parse_args()
    password = getpass.getpass("New operator password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        parser.error("Passwords do not match")
    try:
        password_hash = hash_password(password)
    except ValueError as error:
        parser.error(str(error))

    with SessionLocal() as db:
        if db.query(User).filter((User.username == args.username) | (User.email == args.email)).first():
            parser.error("Username or email is already registered")
        db.add(
            User(
                id=uuid.uuid4(),
                username=args.username,
                email=args.email,
                role=args.role,
                password_hash=password_hash,
            )
        )
        db.commit()
    print(f"Created {args.role} operator {args.username!r}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
