"""Authentication, Argon2id password hashing, session management, and RBAC helpers.

Provides:
- Argon2id password hashing and constant-time verification.
- Per-key brute-force rate limiting (5 failed attempts -> 15-minute lockout).
- HttpOnly session cookies and Bearer token resolution (plus dev/test-only
  legacy staff tokens).
- FastAPI dependencies (``get_current_user``, ``require_role``) and a CLI
  subcommand to bootstrap the initial administrator account.
"""
import base64
import json
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from fastapi import Cookie, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from .observability import event as log_event
from .store import db

AUTH_COOKIE = "mira_auth"
VISITOR_COOKIE = "mira_session"

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Argon2id parameters
ARGON2_MEMORY = 65536  # 64 MB
ARGON2_ITERATIONS = 2
ARGON2_LANES = 4
ARGON2_KEY_LEN = 32
ARGON2_SALT_LEN = 16

RoleType = Literal["guest", "traveller", "staff", "approver", "admin"]
StatusType = Literal["active", "deactivated"]


def hash_password(password: str) -> str:
    """Hashes a password using standard Argon2id with PyCA cryptography."""
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    salt = os.urandom(ARGON2_SALT_LEN)
    kdf = Argon2id(
        salt=salt,
        length=ARGON2_KEY_LEN,
        iterations=ARGON2_ITERATIONS,
        lanes=ARGON2_LANES,
        memory_cost=ARGON2_MEMORY,
    )
    derived = kdf.derive(password.encode("utf-8"))
    salt_b64 = base64.b64encode(salt).decode("ascii")
    derived_b64 = base64.b64encode(derived).decode("ascii")
    return f"$argon2id$v=19$m={ARGON2_MEMORY},t={ARGON2_ITERATIONS},p={ARGON2_LANES}${salt_b64}${derived_b64}"


def verify_password(password: str, hashed: str) -> bool:
    """Verifies a password against an Argon2id hash in constant time."""
    try:
        parts = hashed.split("$")
        # Format: ['', 'argon2id', 'v=19', 'm=...,t=...,p=...', '<salt>', '<hash>']
        if len(parts) != 6 or parts[1] != "argon2id":
            return False
        params = dict(item.split("=") for item in parts[3].split(","))
        m = int(params["m"])
        t = int(params["t"])
        p = int(params["p"])
        salt = base64.b64decode(parts[4])
        derived = base64.b64decode(parts[5])

        kdf = Argon2id(salt=salt, length=len(derived), iterations=t, lanes=p, memory_cost=m)
        kdf.verify(password.encode("utf-8"), derived)
        return True
    except (InvalidKey, Exception):
        return False


def check_brute_force(conn, key: str) -> None:
    """Checks whether the key (email or IP) is locked out due to brute force."""
    now = datetime.now(timezone.utc).timestamp()
    row = conn.execute("SELECT attempts, locked_until FROM login_attempts WHERE key=?", (key,)).fetchone()
    if row and row["locked_until"] > now:
        remaining = int(row["locked_until"] - now)
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed login attempts. Please try again in {remaining} seconds.",
        )


def record_failed_login(conn, key: str) -> None:
    """Increments failed login attempts and locks out if threshold reached."""
    now = datetime.now(timezone.utc).timestamp()
    row = conn.execute("SELECT attempts, last_attempt FROM login_attempts WHERE key=?", (key,)).fetchone()
    if row and (now - row["last_attempt"]) < 900:
        new_attempts = row["attempts"] + 1
        locked_until = (now + 900) if new_attempts >= 5 else 0
        conn.execute(
            "UPDATE login_attempts SET attempts=?, last_attempt=?, locked_until=? WHERE key=?",
            (new_attempts, now, locked_until, key),
        )
        conn.commit()
        if new_attempts >= 5:
            raise HTTPException(429, "Too many failed login attempts. Please try again in 15 minutes.")
    else:
        conn.execute(
            "INSERT OR REPLACE INTO login_attempts(key, attempts, last_attempt, locked_until) VALUES (?, 1, ?, 0)",
            (key, now),
        )
        conn.commit()


def clear_failed_login(conn, key: str) -> None:
    """Clears failed login counter upon successful authentication."""
    conn.execute("DELETE FROM login_attempts WHERE key=?", (key,))


class UserProfile(BaseModel):
    """Publicly safe user profile returned by auth dependencies and endpoints."""

    id: str
    email: str
    full_name: str
    role: RoleType
    status: StatusType
    phone: str = ""
    preferences: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class RegisterInput(BaseModel):
    """Request payload for traveller self-registration."""

    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(default="", max_length=30)
    preferences: dict[str, Any] = Field(default_factory=dict)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalize email to lowercase and validate basic address syntax."""
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format.")
        return v


class LoginInput(BaseModel):
    """Request payload for email/password sign-in."""

    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    remember: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalize email to lowercase and validate basic address syntax."""
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format.")
        return v


class ProfileUpdateInput(BaseModel):
    """Partial update payload for the authenticated user's profile."""

    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    preferences: dict[str, Any] | None = None


class PasswordChangeInput(BaseModel):
    """Request payload for changing an authenticated user's password."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserRoleUpdateInput(BaseModel):
    """Admin-only payload to update a user's role or active/deactivated status."""

    role: RoleType | None = None
    status: StatusType | None = None


def audit_log(conn, actor: str, action: str, target: str, outcome: str = "success") -> None:
    """Appends an immutable audit event without recording sensitive credentials."""
    conn.execute(
        "INSERT INTO audit(actor, action, target) VALUES (?, ?, ?)",
        (actor, f"{action}:{outcome}" if outcome != "success" else action, target),
    )


def ensure_user_visitor(
    conn,
    user_id: str,
    visitor_id: str | None = None,
    remember: bool = False,
) -> str:
    """Return a visitor ID owned by ``user_id``, rotating if missing or owned by another user."""
    if visitor_id:
        row = conn.execute("SELECT id, user_id FROM visitors WHERE id=?", (visitor_id,)).fetchone()
        if row and row["user_id"] in (None, user_id):
            if row["user_id"] is None:
                conn.execute("UPDATE visitors SET user_id=?, remember=? WHERE id=? AND user_id IS NULL",
                             (user_id, int(remember), visitor_id))
            return visitor_id
    new_vid = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO visitors(id, remember, user_id) VALUES (?, ?, ?)", (new_vid, int(remember), user_id))
    return new_vid


def create_user_session(
    conn,
    user_id: str,
    visitor_id: str | None = None,
    remember: bool = False,
    ip: str = "",
    ua: str = "",
) -> tuple[str, str]:
    """Creates a new authenticated session in SQLite and returns (token, expires_at_iso)."""
    token = secrets.token_urlsafe(32)
    duration = timedelta(days=30) if remember else timedelta(days=1)
    now = datetime.now(timezone.utc)
    expires_at = now + duration
    expires_at_iso = expires_at.isoformat()

    valid_visitor_id = None
    if visitor_id:
        row = conn.execute("SELECT id FROM visitors WHERE id=?", (visitor_id,)).fetchone()
        if row:
            valid_visitor_id = row["id"]

    conn.execute(
        """INSERT INTO user_sessions(id, user_id, visitor_id, created_at, expires_at, revoked, ip_address, user_agent)
           VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
        (token, user_id, valid_visitor_id, now.isoformat(), expires_at_iso, ip, ua),
    )

    if valid_visitor_id:
        # Link visitor to user account
        conn.execute("UPDATE visitors SET user_id=? WHERE id=? AND user_id IS NULL", (user_id, valid_visitor_id))

    return token, expires_at_iso


def set_auth_cookie(response: Response, token: str, remember: bool = False) -> None:
    """Sets a secure HttpOnly cookie with appropriate SameSite and expiration."""
    max_age = 2592000 if remember else 86400  # 30 days vs 24 hours
    is_secure = os.getenv("MIRA_SECURE_COOKIE") == "1"
    response.set_cookie(
        AUTH_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=max_age,
        secure=is_secure,
    )


def clear_auth_cookie(response: Response) -> None:
    """Clears the authentication cookie."""
    is_secure = os.getenv("MIRA_SECURE_COOKIE") == "1"
    response.delete_cookie(AUTH_COOKIE, path="/", httponly=True, samesite="lax", secure=is_secure)


def bootstrap_admin(force_email: str | None = None, force_password: str | None = None) -> bool:
    """Initializes the root admin user if explicitly configured via environment or CLI parameters."""
    admin_email = (force_email or os.getenv("MIRA_ADMIN_EMAIL", "admin@ceyloncompass.com")).strip().lower()
    admin_password = (force_password or os.getenv("MIRA_ADMIN_PASSWORD", "")).strip()

    if not admin_password or len(admin_password) < 8:
        # Never bootstrap with unconfigured or hardcoded credentials
        return False

    if not admin_email or not EMAIL_REGEX.match(admin_email):
        admin_email = "admin@ceyloncompass.com"

    with db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE role='admin'").fetchone()
        if existing:
            return True

        user_id = str(uuid4())
        hashed = hash_password(admin_password)
        conn.execute(
            """INSERT INTO users(id, email, password_hash, full_name, role, status, phone, preferences)
               VALUES (?, ?, ?, 'System Administrator', 'admin', 'active', '', '{}')""",
            (user_id, admin_email, hashed),
        )
        audit_log(conn, "system", "bootstrap_admin", user_id)
        log_event("AUTH", "admin.bootstrapped")
        return True


def get_current_user_optional(
    request: Request,
    auth_token: str | None = Cookie(None, alias=AUTH_COOKIE),
    authorization: str = Header(default=""),
) -> UserProfile | None:
    """Retrieves current user from session cookie or Bearer header without raising."""
    # 1. Check HttpOnly session cookie or Bearer session token
    token_to_check = auth_token
    if not token_to_check and authorization.startswith("Bearer "):
        token_to_check = authorization.removeprefix("Bearer ").strip()

    if token_to_check:
        with db() as conn:
            row = conn.execute(
                """SELECT u.id, u.email, u.full_name, u.role, u.status, u.phone, u.preferences, u.created_at,
                          s.revoked, s.expires_at
                   FROM user_sessions s
                   JOIN users u ON u.id = s.user_id
                   WHERE s.id = ?""",
                (token_to_check,),
            ).fetchone()

            if row:
                if row["revoked"] == 1:
                    return None
                try:
                    expires_dt = datetime.fromisoformat(row["expires_at"])
                    if expires_dt < datetime.now(timezone.utc):
                        return None
                except Exception:
                    pass

                if row["status"] != "active":
                    raise HTTPException(403, "Account is deactivated.")

                prefs = json.loads(row["preferences"]) if row["preferences"] else {}
                return UserProfile(
                    id=row["id"],
                    email=row["email"],
                    full_name=row["full_name"],
                    role=row["role"],
                    status=row["status"],
                    phone=row["phone"] or "",
                    preferences=prefs,
                    created_at=row["created_at"],
                )

    # 2. Check Bearer token (for legacy staff tokens, restricted to dev/test mode)
    if authorization.startswith("Bearer "):
        val = authorization.removeprefix("Bearer ").strip()
        allow_legacy = (
            os.getenv("MIRA_ALLOW_LEGACY_TOKENS") == "1"
            or os.getenv("PYTEST_CURRENT_TEST") is not None
            or os.getenv("ENVIRONMENT") in ("development", "test")
            or os.getenv("MIRA_ENV") in ("development", "test")
            or os.getenv("NODE_ENV") in ("development", "test")
        )
        if allow_legacy:
            for name in ("admin", "approver", "editor", "staff"):
                token = os.getenv(f"MIRA_{name.upper()}_TOKEN", "")
                if len(token) >= 24 and secrets.compare_digest(val, token):
                    mapped_role = "approver" if name == "editor" else name
                    email = f"{name}@ceyloncompass.internal"
                    with db() as conn:
                        existing_user = conn.execute("SELECT status FROM users WHERE email = ?", (email,)).fetchone()
                        if existing_user and existing_user["status"] != "active":
                            raise HTTPException(403, "Account is deactivated.")
                    return UserProfile(
                        id=f"token-{name}",
                        email=email,
                        full_name=f"Staff {name.capitalize()}",
                        role=mapped_role if mapped_role in ("admin", "approver", "staff") else "staff",
                        status="active",
                        phone="",
                        preferences={},
                        created_at="2026-01-01T00:00:00Z",
                    )

    return None


def get_current_user(
    user: UserProfile | None = Depends(get_current_user_optional),
) -> UserProfile:
    """Enforces that a user is authenticated."""
    if not user:
        raise HTTPException(401, "Authentication required. Please sign in.")
    return user


def require_role(*roles: RoleType):
    """Enforces that the user has at least one of the specified roles (Admin is always permitted)."""
    def check_permissions(user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if user.role == "admin" or user.role in roles:
            return user
        raise HTTPException(403, f"Insufficient permissions. Required: {', '.join(roles)}")
    return check_permissions


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Ceylon Compass Authentication Management")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    bootstrap_cmd = subparsers.add_parser("bootstrap", help="Bootstrap root administrator account")
    bootstrap_cmd.add_argument("--email", default="admin@ceyloncompass.com", help="Admin email address")
    bootstrap_cmd.add_argument("--password", required=True, help="Admin password (minimum 8 characters)")

    args = parser.parse_args()
    if args.subcommand == "bootstrap":
        if len(args.password) < 8:
            print("Error: Password must be at least 8 characters.", file=sys.stderr)
            sys.exit(1)
        ok = bootstrap_admin(force_email=args.email, force_password=args.password)
        if ok:
            print(f"Administrator successfully initialized: {args.email}")
        else:
            print("Administrator bootstrap failed.", file=sys.stderr)
            sys.exit(1)

