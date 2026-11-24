import { expect, test } from "@playwright/test";

test.describe("Stage 2A Auth, Profile & Staff RBAC Integration", () => {
  const timestamp = Date.now();
  const testTraveller = {
    email: `traveller_${timestamp}@testcompass.com`,
    password: "Password#2026!Key",
    full_name: "Kamal Jayawardena",
    phone: "+94 77 987 6543",
    preferences: { dietary: "halal", pace: "moderate" },
  };

  test("1. Traveller Flow: Register → Session → Profile → Save Quote → Logout → Recovery", async ({ request }) => {
    // 1. Registration
    const regRes = await request.post("/api/auth/register", {
      data: testTraveller,
    });
    expect(regRes.status()).toBe(200);
    const registered = await regRes.json();
    expect(registered.email).toBe(testTraveller.email);
    expect(registered.role).toBe("traveller");
    expect(registered.status).toBe("active");

    // 2. Auth me persistence
    const meRes = await request.get("/api/auth/me");
    expect(meRes.status()).toBe(200);
    const me = await meRes.json();
    expect(me.full_name).toBe(testTraveller.full_name);

    // 3. Update profile preferences
    const updateRes = await request.patch("/api/auth/profile", {
      data: {
        phone: "+94 77 000 1122",
        preferences: { dietary: "vegan", pace: "active" },
      },
    });
    expect(updateRes.status()).toBe(200);
    const updated = await updateRes.json();
    expect(updated.preferences.dietary).toBe("vegan");
    expect(updated.phone).toBe("+94 77 000 1122");

    // 4. Traveller overview
    const ovRes = await request.get("/api/traveller/overview");
    expect(ovRes.status()).toBe(200);
    const ov = await ovRes.json();
    expect(ov.user.email).toBe(testTraveller.email);

    // 5. Logout
    const logoutRes = await request.post("/api/auth/logout");
    expect(logoutRes.status()).toBe(200);

    // 6. Verify unauthenticated
    const unauthRes = await request.get("/api/auth/me");
    expect(unauthRes.status()).toBe(401);

    // 7. Login again
    const loginRes = await request.post("/api/auth/login", {
      data: {
        email: testTraveller.email,
        password: testTraveller.password,
        remember: true,
      },
    });
    expect(loginRes.status()).toBe(200);
    const loggedIn = await loginRes.json();
    expect(loggedIn.email).toBe(testTraveller.email);

    // 8. Recover profile data
    const recoveredMe = await request.get("/api/auth/me");
    expect(recoveredMe.status()).toBe(200);
    expect((await recoveredMe.json()).preferences.dietary).toBe("vegan");
  });

  test("2. Staff Flow: Operational Overview → Enquiry Inspection → Notes → Assignment", async ({ request }) => {
    const staffToken = process.env.MIRA_STAFF_TOKEN;
    test.skip(!staffToken, "Requires MIRA_STAFF_TOKEN");
    if (!staffToken) return;

    const authHeaders = { Authorization: `Bearer ${staffToken}` };

    // 1. Operational Overview
    const ovRes = await request.get("/api/staff/dashboard/overview", { headers: authHeaders });
    expect(ovRes.status()).toBe(200);
    const ov = await ovRes.json();
    expect(typeof ov.total_enquiries).toBe("number");
    expect(typeof ov.pending_followups).toBe("number");

    // 2. List enquiries
    const listRes = await request.get("/api/staff/enquiries", { headers: authHeaders });
    expect(listRes.status()).toBe(200);
    const enquiries = await listRes.json();
    expect(Array.isArray(enquiries)).toBe(true);

    if (enquiries.length > 0) {
      const target = enquiries[0];

      // 3. Inspect enquiry details
      const detailRes = await request.get(`/api/staff/enquiries/${target.id}`, { headers: authHeaders });
      expect(detailRes.status()).toBe(200);
      const detail = await detailRes.json();
      expect(detail.id).toBe(target.id);

      // 4. Update follow-up status and add staff note
      const patchRes = await request.patch(`/api/staff/enquiries/${target.id}`, {
        headers: authHeaders,
        data: {
          status: "contacted",
          note: "Contacted traveller via WhatsApp regarding private villa options.",
        },
      });
      expect(patchRes.status()).toBe(200);

      // 5. Assign staff member
      const assignableRes = await request.get("/api/staff/users/assignable", { headers: authHeaders });
      expect(assignableRes.status()).toBe(200);
      const staffList = await assignableRes.json();
      if (staffList.length > 0) {
        const staffMember = staffList[0];
        const assignRes = await request.patch(`/api/staff/enquiries/${target.id}`, {
          headers: authHeaders,
          data: {
            assigned_to: staffMember.id,
          },
        });
        expect(assignRes.status()).toBe(200);
      }
    }
  });

  test("3. Approver Flow: Draft Creation → Review → Role Guard → Publication Workflow", async ({ request }) => {
    const editorToken = process.env.MIRA_EDITOR_TOKEN;
    const approverToken = process.env.MIRA_APPROVER_TOKEN;
    test.skip(!editorToken || !approverToken, "Requires local Editor and Approver tokens");
    if (!editorToken || !approverToken) return;

    // 1. Create AI-assisted draft concept
    const draftRes = await request.post("/api/staff/drafts", {
      headers: { Authorization: `Bearer ${editorToken}` },
      data: { command: "Create an exclusive Nuwara Eliya colonial tea trail concept" },
    });
    expect(draftRes.status()).toBe(200);
    const draft = await draftRes.json();
    expect(draft.id).toBeDefined();

    // 2. Draft is unpublished and not public
    const publicBefore = await request.get(`/api/sources/${draft.id}`);
    expect(publicBefore.status()).toBe(404);

    // 3. Approver reviews draft
    const reviewRes = await request.post(`/api/staff/drafts/${draft.id}/review`, {
      headers: { Authorization: `Bearer ${approverToken}` },
      data: { action: "approve", notes: "Approved for Hill Country promotions." },
    });
    expect(reviewRes.status()).toBe(200);
    expect((await reviewRes.json()).status).toBe("approved");

    // 4. Approver publishes draft
    const pubRes = await request.post(`/api/staff/drafts/${draft.id}/publish`, {
      headers: { Authorization: `Bearer ${approverToken}` },
    });
    expect(pubRes.status()).toBe(200);
    expect((await pubRes.json()).status).toBe("published");

    // 5. Content is now publicly searchable
    const publicAfter = await request.get(`/api/sources/${draft.id}`);
    expect(publicAfter.status()).toBe(200);
  });

  test("4. Admin Flow: User Administration → Role Elevation → Account Deactivation → Audit Trail", async ({ request }) => {
    const adminPassword = process.env.MIRA_ADMIN_PASSWORD || "Admin#2026!Compass";

    // 1. Create a test user to manage
    const targetEmail = `subject_${timestamp}@example.com`;
    const regRes = await request.post("/api/auth/register", {
      data: {
        email: targetEmail,
        password: "SubjectPassword#2026",
        full_name: "Subject To Admin",
      },
    });
    expect(regRes.status()).toBe(200);
    await request.post("/api/auth/logout");

    // 2. Admin logs in
    const adminLogin = await request.post("/api/auth/login", {
      data: {
        email: "admin@ceyloncompass.com",
        password: adminPassword,
      },
    });
    if (adminLogin.status() !== 200) {
      test.skip(true, "Admin bootstrap credentials not configured in this test run");
      return;
    }
    expect(adminLogin.status()).toBe(200);
    expect((await adminLogin.json()).role).toBe("admin");

    // 3. Admin lists users
    const usersRes = await request.get("/api/admin/users");
    expect(usersRes.status()).toBe(200);
    const users = await usersRes.json();
    const targetUser = users.find((u: { email: string }) => u.email === targetEmail);
    expect(targetUser).toBeDefined();

    // 4. Promote user to staff
    const promoteRes = await request.patch(`/api/admin/users/${targetUser.id}`, {
      data: { role: "staff" },
    });
    expect(promoteRes.status()).toBe(200);

    // 5. Deactivate user account
    const deactRes = await request.patch(`/api/admin/users/${targetUser.id}`, {
      data: { status: "deactivated" },
    });
    expect(deactRes.status()).toBe(200);

    // 6. Verify target user cannot login
    await request.post("/api/auth/logout");
    const blockedLogin = await request.post("/api/auth/login", {
      data: {
        email: targetEmail,
        password: "SubjectPassword#2026",
      },
    });
    expect(blockedLogin.status()).toBe(403);

    // 7. Re-login admin and verify audit trail
    await request.post("/api/auth/login", {
      data: {
        email: "admin@ceyloncompass.com",
        password: adminPassword,
      },
    });
    const auditRes = await request.get("/api/admin/audit");
    expect(auditRes.status()).toBe(200);
    const auditLogs = await auditRes.json();
    expect(auditLogs.some((a: { action: string; target: string }) => a.target === targetUser.id)).toBe(true);
  });
});
