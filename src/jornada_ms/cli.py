"""Operational commands for local provisioning."""

# SQL statements are kept readable as complete statements in this small module.
# ruff: noqa: E501

import argparse
import getpass
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

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


def create_organization() -> None:
    """Create the first company and branch for a local installation."""

    parser = argparse.ArgumentParser(description="Create a JornadaMS company and branch")
    parser.add_argument("--name", required=True, help="Company name")
    parser.add_argument("--cnpj", required=True, help="Company CNPJ, only digits")
    parser.add_argument("--branch", default="Matriz", help="Branch name")
    parser.add_argument("--branch-code", default="MATRIZ", help="Branch code")
    parser.add_argument("--timezone", default="America/Sao_Paulo", help="IANA timezone")
    args = parser.parse_args()
    if len(args.cnpj) != 14 or not args.cnpj.isdigit():
        parser.error("CNPJ must contain exactly 14 digits")

    settings = get_settings()
    database = Database.from_settings(settings)
    company_id = str(uuid4())
    branch_id = str(uuid4())
    try:
        with database.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO companies (id, name, cnpj, default_timezone) VALUES (:id, :name, :cnpj, :timezone)"
                ),
                {
                    "id": company_id,
                    "name": args.name.strip(),
                    "cnpj": args.cnpj,
                    "timezone": args.timezone,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO branches (id, company_id, name, code, timezone) VALUES (:id, :company_id, :name, :code, :timezone)"
                ),
                {
                    "id": branch_id,
                    "company_id": company_id,
                    "name": args.branch.strip(),
                    "code": args.branch_code.strip(),
                    "timezone": args.timezone,
                },
            )
    except IntegrityError as exc:
        parser.error(f"Company or branch already exists: {exc.orig}")
    finally:
        database.dispose()
    print(f"Company created: {company_id}")
    print(f"Branch created: {branch_id}")


if __name__ == "__main__":
    create_user()
