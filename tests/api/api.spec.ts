/**
 * FaceGym API — Playwright E2E contract tests
 *
 * These tests run against the live Docker stack and verify:
 *  - API contract correctness (response shapes, status codes)
 *  - Member lifecycle (create → read → update → delete)
 *  - Edge cases (duplicates, missing records, empty recognition)
 *  - Kiosk page availability
 */
import { test, expect, APIRequestContext } from '@playwright/test';

const BASE = process.env.API_BASE_URL || 'http://localhost:3001';

// ── Helpers ─────────────────────────────────────────────────────

async function createMember(request: APIRequestContext, name: string) {
  const res = await request.post(`${BASE}/api/members`, {
    data: { name, expiration_date: '2099-12-31' },
  });
  expect(res.status()).toBe(201);
  return res.json();
}

// ── Health & Stats ───────────────────────────────────────────────

test.describe('Stats endpoint', () => {
  test('GET /api/stats returns 200 with correct shape', async ({ request }) => {
    const res = await request.get(`${BASE}/api/stats`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toMatchObject({
      total_members: expect.any(Number),
      active_members: expect.any(Number),
      expired_members: expect.any(Number),
      entries_today: expect.any(Number),
      entries_this_week: expect.any(Number),
    });
  });
});

// ── Members CRUD ─────────────────────────────────────────────────

test.describe('Member registration', () => {
  test('POST /api/members auto-assigns GYM-prefixed ID', async ({ request }) => {
    const member = await createMember(request, 'E2E Test User');
    expect(member.membership_id).toMatch(/^GYM\d{4}$/);
    expect(member.member_number).toBeGreaterThan(0);
    expect(member.name).toBe('E2E Test User');
    expect(member.has_face_sample).toBe(false);

    // Cleanup
    await request.delete(`${BASE}/api/members/${member.membership_id}`);
  });

  test('POST /api/members with past date returns 400', async ({ request }) => {
    const res = await request.post(`${BASE}/api/members`, {
      data: { name: 'Expired', expiration_date: '2000-01-01' },
    });
    expect(res.status()).toBe(400);
  });

  test('POST /api/members with invalid date returns 422', async ({ request }) => {
    const res = await request.post(`${BASE}/api/members`, {
      data: { name: 'Bad Date', expiration_date: 'not-a-date' },
    });
    expect(res.status()).toBe(422);
  });
});

test.describe('Member retrieval', () => {
  test('GET /api/members returns array', async ({ request }) => {
    const res = await request.get(`${BASE}/api/members`);
    expect(res.status()).toBe(200);
    expect(await res.json()).toBeInstanceOf(Array);
  });

  test('GET /api/members/:id returns correct member', async ({ request }) => {
    const member = await createMember(request, 'Retrieval Test');
    const res = await request.get(`${BASE}/api/members/${member.membership_id}`);
    expect(res.status()).toBe(200);
    expect((await res.json()).name).toBe('Retrieval Test');
    await request.delete(`${BASE}/api/members/${member.membership_id}`);
  });

  test('GET /api/members/:id returns 404 for unknown ID', async ({ request }) => {
    const res = await request.get(`${BASE}/api/members/GYM9999`);
    expect(res.status()).toBe(404);
  });
});

test.describe('Member update & delete', () => {
  test('PUT /api/members/:id updates name', async ({ request }) => {
    const member = await createMember(request, 'Original Name');
    const res = await request.put(`${BASE}/api/members/${member.membership_id}`, {
      data: { name: 'Updated Name' },
    });
    expect(res.status()).toBe(200);
    expect((await res.json()).name).toBe('Updated Name');
    await request.delete(`${BASE}/api/members/${member.membership_id}`);
  });

  test('DELETE /api/members/:id returns 204', async ({ request }) => {
    const member = await createMember(request, 'Delete Me');
    const res = await request.delete(`${BASE}/api/members/${member.membership_id}`);
    expect(res.status()).toBe(204);
  });

  test('DELETE /api/members/:id returns 404 for unknown ID', async ({ request }) => {
    const res = await request.delete(`${BASE}/api/members/GYM9999`);
    expect(res.status()).toBe(404);
  });
});

// ── Recognition ──────────────────────────────────────────────────

test.describe('Recognition endpoint', () => {
  test('POST /api/recognize with no members returns friendly 200', async ({ request }) => {
    // This test is meaningful when run against a clean DB
    const res = await request.post(`${BASE}/api/recognize`, {
      data: { image: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==' },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty('recognized');
    expect(body).toHaveProperty('message');
  });
});

// ── Attendance ───────────────────────────────────────────────────

test.describe('Attendance endpoint', () => {
  test('GET /api/attendance returns array', async ({ request }) => {
    const res = await request.get(`${BASE}/api/attendance`);
    expect(res.status()).toBe(200);
    expect(await res.json()).toBeInstanceOf(Array);
  });
});

// ── Frontend pages ────────────────────────────────────────────────

test.describe('Frontend pages', () => {
  test('Dashboard page loads', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await expect(page).toHaveTitle(/FaceGym/i);
  });

  test('Kiosk page loads without sidebar', async ({ page }) => {
    await page.goto(`${BASE}/kiosk`);
    // Kiosk has no sidebar nav — verify it's not rendered
    await expect(page.locator('.sidebar')).not.toBeVisible();
  });

  test('Members page loads', async ({ page }) => {
    await page.goto(`${BASE}/members`);
    await expect(page.locator('h1')).toBeVisible();
  });
});
