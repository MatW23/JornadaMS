"""Operational commands for local provisioning."""

import argparse
import getpass

from jornada_ms.config import get_settings
from jornada_ms.db.session import Database
from jornada_ms.modules.identity.service import IdentityService


def create_user() -> None:
    """Create an initial user without placing the password in shell history."""

    parser = argparse.ArgumentParser(description="Create a JornadaMS user")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--role", action="append", default=[], help="Role (repeatable)")
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        parser.error("Passwords do not match")

    settings = get_settings()
    database = Database.from_settings(settings)
    try:
        user_id = IdentityService(database, settings).create_user(
            args.email,
            password,
            args.role or ["ADMIN"],
        )
    finally:
        database.dispose()
    print(f"User created: {user_id}")


if __name__ == "__main__":
    create_user()
