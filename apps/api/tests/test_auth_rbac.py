"""Tests for user registration, Argon2id hashing, brute-force lockouts, session isolation, and RBAC."""
import json
from uuid import uuid4
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from conftest import headers, quotes, turn
from mira import store
from mira.auth import hash_password, verify_password
from mira.main import app


# ==============================================================================
# 1. REGISTRATION & LOGIN
# ==============================================================================

def test_traveller_registration_success(app_client):
    """Registering a new account creates a user with 'traveller' role and sets session cookie."""
    email = f"traveller_{uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "StrongPassword2026!",
        "full_name": "Saman Perera",
        "phone": "+94 77 123 4567",
        "preferences": {"dietary": "vegetarian", "pace": "relaxed"},
    }
    res = app_client.post("/api/auth/register", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == email
    assert data["role"] == "traveller"
    assert data["status"] == "active"
    assert data["full_name"] == "Saman Perera"
    assert data["preferences"]["dietary"] == "vegetarian"
    assert "mira_auth" in res.headers["set-cookie"]

    # Verify user can access /api/auth/me immediately
    me_res = app_client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email


def test_public_registration_cannot_assign_privileged_roles(app_client):
    """An attacker passing 'role': 'admin' or 'approver' in register payload is ignored."""
    email = f"attacker_{uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "StrongPassword2026!",
        "full_name": "Privilege Escalation Attempt",
        "role": "admin",  # Attacker attempt
    }
    res = app_client.post("/api/auth/register", json=payload)
    assert res.status_code == 200
    assert res.json()["role"] == "traveller"

    # Confirm in DB directly
    with store.db() as conn:
        row = conn.execute("SELECT role FROM users WHERE email=?", (email,)).fetchone()
        assert row["role"] == "traveller"


def test_duplicate_registration_rejected(app_client):
    """Registering with an already existing email returns 400 Bad Request."""
    email = f"dupe_{uuid4().hex[:8]}@example.com"
    payload = {"email": email, "password": "Password123!", "full_name": "Original User"}
    assert app_client.post("/api/auth/register", json=payload).status_code == 200
    # Duplicate attempt
    res = app_client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"].lower()


def test_login_success_and_logout(app_client):
    """Logging in sets HttpOnly cookie; logging out revokes session and clears cookie."""
    email = f"user_{uuid4().hex[:8]}@example.com"
    pwd = "MySecretPassword2026!"
    app_client.post("/api/auth/register", json={"email": email, "password": pwd, "full_name": "Test User"})

    # Explicit login
    with TestClient(app) as client:
        login_res = client.post("/api/auth/login", json={"email": email, "password": pwd, "remember": True})
        assert login_res.status_code == 200
        assert "mira_auth" in login_res.headers["set-cookie"]
        assert "max-age=2592000" in login_res.headers["set-cookie"].lower()

        # Check authenticated identity
        assert client.get("/api/auth/me").status_code == 200

        # Logout
        logout_res = client.post("/api/auth/logout")
        assert logout_res.status_code == 200
        assert logout_res.json()["logged_out"] is True

        # Subsequent authenticated calls fail
        assert client.get("/api/auth/me").status_code == 401


def test_login_invalid_credentials(app_client):
    """Invalid password returns 401 and does not set auth cookie."""
    email = f"user_{uuid4().hex[:8]}@example.com"
    app_client.post("/api/auth/register", json={"email": email, "password": "CorrectPassword123!", "full_name": "User"})

    with TestClient(app) as client:
        res = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword!"})
        assert res.status_code == 401
        assert "invalid" in res.json()["detail"].lower()
        assert "mira_auth" not in res.headers.get("set-cookie", "")


def test_brute_force_lockout(app_client):
    """5 consecutive failed logins trigger a 429 lockout."""
    email = f"victim_{uuid4().hex[:8]}@example.com"
    app_client.post("/api/auth/register", json={"email": email, "password": "CorrectPassword123!", "full_name": "Victim"})

    with TestClient(app) as client:
        for _ in range(4):
            res = client.post("/api/auth/login", json={"email": email, "password": "BadPassword"})
            assert res.status_code == 401
        # 5th attempt triggers lockout
        res5 = client.post("/api/auth/login", json={"email": email, "password": "BadPassword"})
        assert res5.status_code == 429
        assert "too many" in res5.json()["detail"].lower()


# ==============================================================================
# 2. PASSWORD HASHING & SECURITY
# ==============================================================================

def test_argon2id_password_hashing():
    """Argon2id produces standard format, unique salts, and constant-time verification."""
    pwd = "ComplexPassword2026!"
    h1 = hash_password(pwd)
    h2 = hash_password(pwd)
    assert h1 != h2  # Salt uniqueness
    assert h1.startswith("$argon2id$v=19$m=65536,t=2,p=4$")
    assert verify_password(pwd, h1)
    assert verify_password(pwd, h2)
    assert not verify_password("WrongPassword!", h1)
    assert not verify_password("", h1)


def test_password_change_revokes_other_sessions(app_client):
    """Changing password updates hash and revokes other active sessions for that user."""
    email = f"pwchange_{uuid4().hex[:8]}@example.com"
    pwd1 = "OldPassword123!"
    pwd2 = "NewStrongPassword2026!"
    app_client.post("/api/auth/register", json={"email": email, "password": pwd1, "full_name": "Change User"})

    # Session A
    client_a = TestClient(app)
    client_a.post("/api/auth/login", json={"email": email, "password": pwd1})
    assert client_a.get("/api/auth/me").status_code == 200

    # Session B changes password
    client_b = TestClient(app)
    client_b.post("/api/auth/login", json={"email": email, "password": pwd1})
    chg_res = client_b.post("/api/auth/password", json={"current_password": pwd1, "new_password": pwd2})
    assert chg_res.status_code == 200

    # Session A is now revoked
    assert client_a.get("/api/auth/me").status_code == 401

    # Session B remains valid
    assert client_b.get("/api/auth/me").status_code == 200

    # New login works with pwd2, fails with pwd1
    client_c = TestClient(app)
    assert client_c.post("/api/auth/login", json={"email": email, "password": pwd1}).status_code == 401
    assert client_c.post("/api/auth/login", json={"email": email, "password": pwd2}).status_code == 200


# ==============================================================================
# 3. TRAVELLER PROFILE MANAGEMENT & OWNERSHIP
# ==============================================================================

def test_traveller_profile_update_and_privilege_boundary(app_client):
    """Traveller can update full_name, phone, preferences; cannot change role or status."""
    email = f"profile_{uuid4().hex[:8]}@example.com"
    app_client.post("/api/auth/register", json={"email": email, "password": "Password123!", "full_name": "Initial Name"})

    # Update profile
    patch_res = app_client.patch("/api/auth/profile", json={
        "full_name": "Updated Name",
        "phone": "+94 71 999 8888",
        "preferences": {"budget": "luxury", "interests": ["wildlife", "tea estates"]},
        "role": "admin",  # Attempted escalation
    })
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["full_name"] == "Updated Name"
    assert data["phone"] == "+94 71 999 8888"
    assert data["preferences"]["budget"] == "luxury"
    assert data["role"] == "traveller"  # Unchanged!


def test_traveller_overview_and_quote_ownership(app_client):
    """Traveller overview returns last quote and saved quotes for the authenticated user."""
    email = f"trav_{uuid4().hex[:8]}@example.com"
    app_client.post("/api/auth/register", json={"email": email, "password": "Password123!", "full_name": "Traveller One"})

    # Visitor session creates a quote
    t_quote = turn(app_client, "Sigiriya day trip for two adults on 10 January 2027")
    [q] = quotes(t_quote)

    overview = app_client.get("/api/traveller/overview").json()
    assert overview["total_quotes"] >= 1
    assert overview["last_quote"]["id"] == str(q.id)
    assert overview["last_quote"]["total"] == 315

    # Traveller quotes endpoint returns user's quotes
    traveller_quotes = app_client.get("/api/traveller/quotes").json()
    assert len(traveller_quotes) >= 1
    assert traveller_quotes[0]["quote"]["id"] == str(q.id)


def test_cross_user_isolation(app_client):
    """User A's quotes and profile cannot be accessed or booked by User B."""
    # User A
    email_a = f"usera_{uuid4().hex[:8]}@example.com"
    app_client.post("/api/auth/register", json={"email": email_a, "password": "Password123!", "full_name": "User A"})
    t_a = turn(app_client, "Sigiriya day trip for two adults on 10 January 2027")
    [q_a] = quotes(t_a)

    # Logout User A and clear visitor session
    app_client.post("/api/auth/logout")
    app_client.delete("/api/session")

    # User B registers on a new session
    app_client.post("/api/session", json={"remember": False})
    email_b = f"userb_{uuid4().hex[:8]}@example.com"
    app_client.post("/api/auth/register", json={"email": email_b, "password": "Password123!", "full_name": "User B"})

    # User B has no quotes
    assert app_client.get("/api/traveller/quotes").json() == []

    # User B cannot mock-book User A's quote
    book_attempt = app_client.post("/api/bookings/mock", json={"quote": str(q_a.id)})
    assert book_attempt.status_code == 404


# ==============================================================================
# 4. RBAC & PERMISSION MATRIX
# ==============================================================================

def test_unauthorized_staff_and_admin_endpoints(app_client):
    """Unauthenticated guests and travellers cannot access staff or admin routes."""
    # Guest access
    assert app_client.get("/api/staff/dashboard/overview").status_code == 401
    assert app_client.get("/api/staff/enquiries").status_code == 401
    assert app_client.get("/api/admin/users").status_code == 401
    assert app_client.get("/api/admin/audit").status_code == 401

    # Traveller access
    email = f"trav_{uuid4().hex[:8]}@example.com"
    app_client.post("/api/auth/register", json={"email": email, "password": "Password123!", "full_name": "Normal Traveller"})
    assert app_client.get("/api/staff/dashboard/overview").status_code == 403
    assert app_client.get("/api/staff/enquiries").status_code == 403
    assert app_client.get("/api/admin/users").status_code == 403
    assert app_client.get("/api/admin/audit").status_code == 403


def test_staff_role_permissions(app_client):
    """Staff can view dashboard and manage enquiries; cannot approve/publish or manage users."""
    st_headers = headers("staff")
    assert app_client.get("/api/staff/dashboard/overview", headers=st_headers).status_code == 200
    assert app_client.get("/api/staff/enquiries", headers=st_headers).status_code == 200
    assert app_client.get("/api/staff/users/assignable", headers=st_headers).status_code == 200

    # Staff cannot manage users or publish drafts
    assert app_client.get("/api/admin/users", headers=st_headers).status_code == 403
    assert app_client.post("/api/staff/drafts/test/publish", headers=st_headers).status_code == 403


def test_approver_and_human_approval_invariant(app_client):
    """AI draft creation -> Review -> Approver publication -> Search availability."""
    app_headers = headers("approver")

    # 1. Create a draft
    create_res = app_client.post("/api/staff/drafts", json={"command": "Create a concept for Kandy"}, headers=app_headers)
    assert create_res.status_code == 200
    draft_id = create_res.json()["id"]

    # 2. Review draft (approve)
    rev_res = app_client.post(f"/api/staff/drafts/{draft_id}/review", json={"action": "approve", "notes": "Approved for Hill Country promo"}, headers=app_headers)
    assert rev_res.status_code == 200
    assert rev_res.json()["status"] == "approved"

    # 3. Draft is NOT public before publish
    assert app_client.get(f"/api/sources/{draft_id}").status_code == 404

    # 4. Approver publishes
    pub_res = app_client.post(f"/api/staff/drafts/{draft_id}/publish", headers=app_headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "published"

    # 5. Content is now publicly searchable
    assert app_client.get(f"/api/sources/{draft_id}").status_code == 200


def test_admin_user_management_and_audit(app_client):
    """Admin can list users, update roles, activate/deactivate accounts, and inspect audit logs."""
    # Create a test traveller first
    target_email = f"target_{uuid4().hex[:8]}@example.com"
    app_client.post("/api/auth/register", json={"email": target_email, "password": "Password123!", "full_name": "Target User"})
    app_client.post("/api/auth/logout")

    # Log in as initial bootstrapped Admin
    login_admin = app_client.post("/api/auth/login", json={"email": "admin@ceyloncompass.com", "password": "Admin#2026!Compass"})
    assert login_admin.status_code == 200
    assert login_admin.json()["role"] == "admin"

    # Admin lists users
    users = app_client.get("/api/admin/users").json()
    assert isinstance(users, list)
    target = next(u for u in users if u["email"] == target_email)
    assert target["role"] == "traveller"

    # Admin promotes traveller to staff
    promote_res = app_client.patch(f"/api/admin/users/{target['id']}", json={"role": "staff"})
    assert promote_res.status_code == 200

    # Verify role was updated
    refreshed = app_client.get("/api/admin/users").json()
    updated_target = next(u for u in refreshed if u["id"] == target["id"])
    assert updated_target["role"] == "staff"

    # Admin deactivates account
    deact_res = app_client.patch(f"/api/admin/users/{target['id']}", json={"status": "deactivated"})
    assert deact_res.status_code == 200

    # Logout admin
    app_client.post("/api/auth/logout")

    # Target user cannot login when deactivated
    login_res = app_client.post("/api/auth/login", json={"email": target_email, "password": "Password123!"})
    assert login_res.status_code == 403
    assert "deactivated" in login_res.json()["detail"].lower()

    # Log back in as admin and verify audit log contains privileged admin events
    app_client.post("/api/auth/login", json={"email": "admin@ceyloncompass.com", "password": "Admin#2026!Compass"})
    audit_rows = app_client.get("/api/admin/audit").json()
    assert any("admin_update_user" in a["action"] and a["target"] == target["id"] for a in audit_rows)


def test_bootstrap_admin_requires_configured_password(tmp_path, monkeypatch):
    """Admin bootstrap refuses to initialize if no admin password or empty password is provided."""
    from mira.auth import bootstrap_admin
    monkeypatch.setattr(store, "DB", tmp_path / "bootstrap_test.sqlite3")
    monkeypatch.delenv("MIRA_ADMIN_PASSWORD", raising=False)

    store.init()
    assert bootstrap_admin() is False

    with store.db() as conn:
        row = conn.execute("SELECT id FROM users WHERE role='admin'").fetchone()
        assert row is None

    # Provide valid explicit password
    assert bootstrap_admin(force_email="root@ceyloncompass.com", force_password="SecureBoot#2026!Key") is True
    with store.db() as conn:
        row = conn.execute("SELECT email, role FROM users WHERE role='admin'").fetchone()
        assert row["email"] == "root@ceyloncompass.com"
        assert row["role"] == "admin"


def test_deactivated_user_cannot_authenticate_with_session(app_client):
    """If an account is deactivated, existing sessions are blocked with 403."""
    user_email = f"deact_{uuid4().hex[:8]}@example.com"
    app_client.post("/api/auth/register", json={"email": user_email, "password": "StrongPassword2026!", "full_name": "Active To Deact"})

    # Confirm session works
    assert app_client.get("/api/auth/me").status_code == 200

    # Deactivate directly in DB
    with store.db() as conn:
        conn.execute("UPDATE users SET status='deactivated' WHERE email=?", (user_email,))

    # Session access is now forbidden
    me_res = app_client.get("/api/auth/me")
    assert me_res.status_code == 403
    assert "deactivated" in me_res.json()["detail"].lower()


def test_login_with_stale_visitor_cookie_succeeds(app_client):
    """A stale mira_session cookie not in visitors must not cause an IntegrityError on login."""
    email = f"stale_{uuid4().hex[:8]}@example.com"
    pwd = "StrongPassword2026!"
    app_client.post("/api/auth/register", json={"email": email, "password": pwd, "full_name": "Stale Visitor"})

    stale_client = TestClient(app)
    stale_client.cookies.set("mira_session", "stale-nonexistent-visitor-token")
    res = stale_client.post("/api/auth/login", json={"email": email, "password": pwd})
    assert res.status_code == 200, res.text
    assert stale_client.get("/api/auth/me").status_code == 200

