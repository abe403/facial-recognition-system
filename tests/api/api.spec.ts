/**
 * FaceGym API — Playwright E2E contract tests
 */
import { test, expect, APIRequestContext } from '@playwright/test';

const BASE = process.env.API_BASE_URL || 'http://localhost:3001';

// ── Auth Helper ──────────────────────────────────────────────────

let authToken: string;

test.beforeAll(async ({ playwright }) => {
  // Use a fresh request context to login
  const request = await playwright.request.newContext();
  const res = await request.post(`${BASE}/api/auth/login`, {
    form: {
      username: 'admin',
      password: 'admin123',
    },
  });

  if (res.status() !== 200) {
    throw new Error(`Login failed with status ${res.status()}: ${await res.text()}`);
  }

  const data = await res.json();
  authToken = data.access_token;
});

function getAuthHeaders() {
  return { Authorization: `Bearer ${authToken}` };
}

// ── Helpers ─────────────────────────────────────────────────────

async function createMember(request: APIRequestContext, name: string) {
  const res = await request.post(`${BASE}/api/members`, {
    data: { name, expiration_date: '2099-12-31' },
    headers: getAuthHeaders(),
  });
  expect(res.status()).toBe(201);
  return res.json();
}

// ── Health & Stats ───────────────────────────────────────────────

test.describe('Stats endpoint', () => {
  test('GET /api/stats returns 200 with correct shape', async ({ request }) => {
    const res = await request.get(`${BASE}/api/stats`, {
      headers: getAuthHeaders(),
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toMatchObject({
      total_members: expect.any(Number),
      active_members: expect.any(Number),
      expired_members: expect.any(Number),
    });
  });

  test('GET /api/stats returns 401 without token', async ({ request }) => {
    const res = await request.get(`${BASE}/api/stats`);
    expect(res.status()).toBe(401);
  });
});

// ── Members CRUD ─────────────────────────────────────────────────

test.describe('Member registration', () => {
  test('POST /api/members auto-assigns GYM-prefixed ID', async ({ request }) => {
    const member = await createMember(request, 'E2E Test User');
    expect(member.membership_id).toMatch(/^GYM\d{4}$/);
    
    // Cleanup
    await request.delete(`${BASE}/api/members/${member.membership_id}`, {
      headers: getAuthHeaders(),
    });
  });

  test('POST /api/members with past date returns 400', async ({ request }) => {
    const res = await request.post(`${BASE}/api/members`, {
      data: { name: 'Expired', expiration_date: '2000-01-01' },
      headers: getAuthHeaders(),
    });
    expect(res.status()).toBe(400);
  });
});

test.describe('Member retrieval', () => {
  test('GET /api/members returns array', async ({ request }) => {
    const res = await request.get(`${BASE}/api/members`, {
      headers: getAuthHeaders(),
    });
    expect(res.status()).toBe(200);
    expect(await res.json()).toBeInstanceOf(Array);
  });

  test('GET /api/members/:id returns 404 for unknown ID', async ({ request }) => {
    const res = await request.get(`${BASE}/api/members/GYM9999`, {
      headers: getAuthHeaders(),
    });
    expect(res.status()).toBe(404);
  });
});

// ── Recognition (PUBLIC) ──────────────────────────────────────────

test.describe('Recognition endpoint', () => {
  test('POST /api/recognize is public (no token needed)', async ({ request }) => {
    const res = await request.post(`${BASE}/api/recognize`, {
      data: { image: 'data:image/png;base64,iVBORw0KGgo=' },
    });
    expect(res.status()).toBe(200);
  });
});

// ── Frontend pages ────────────────────────────────────────────────

test.describe('Frontend pages', () => {
  test('Dashboard page redirects to login when unauthenticated', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await expect(page).toHaveURL(/.*\/login/);
  });

  test('Kiosk page loads (Public)', async ({ page }) => {
    await page.goto(`${BASE}/kiosk`);
    // Use exact match to avoid strict mode violation with the footer
    await expect(page.getByText('FaceGym', { exact: true })).toBeVisible({ timeout: 10000 });
    // Also verify the scanning hint exists (initial state)
    await expect(page.locator('.kiosk-root')).toBeVisible();
  });
});
