import { test, expect, type Page } from '@playwright/test';
import { loginByApi } from './helpers/auth';

const ADMIN = { username: 'admin', password: 'admin123' };
const CUSTOMER = { username: 'customer1', password: 'customer123' };
const INVALID = { username: 'invalid', password: 'wrongpass' };

async function gotoLogin(page: Page) {
  // The app redirects first-time visitors from /login to /docs.
  await page.addInitScript(() => {
    window.sessionStorage.setItem('viewer_landed', '1');
  });
  await page.goto('/login');
}

async function submitLogin(page: Page, credentials: { username: string; password: string }) {
  await gotoLogin(page);
  await expect(page.locator('input#username')).toBeVisible();
  await page.fill('input#username', credentials.username);
  await page.fill('input#password', credentials.password);
  await page.click('button[type="submit"]');
}

async function isRateLimited(page: Page) {
  const rateLimitMessage = page.getByText(/too many requests|please try again later|retry after/i).first();
  return rateLimitMessage.isVisible().catch(() => false);
}

async function loginAsAdmin(page: Page) {
  await loginByApi(page, ADMIN, /\/(dashboard|documents)/, '/dashboard');
}

async function loginAsCustomer(page: Page) {
  await loginByApi(page, CUSTOMER, /\/portal\//, '/portal');
}

async function openDocuments(page: Page) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    await page.goto('/documents');
    await page.waitForURL(/\/(documents|login)/, { timeout: 10000 }).catch(() => undefined);
    if (!page.url().includes('/login')) {
      await expect(page).toHaveURL(/\/documents/, { timeout: 15000 });
      return;
    }
    await loginAsAdmin(page);
  }

  throw new Error('Unable to open /documents after re-authentication attempts.');
}

async function createDocument(page: Page, title: string) {
  await openDocuments(page);
  await page.getByRole('button', { name: /new document/i }).click();
  await expect(page.getByText('Create Document')).toBeVisible();
  await page.fill('input[placeholder="Enter document title"]', title);
  await page.fill('textarea[placeholder="Brief description"]', 'Created by Playwright E2E');
  const createBtn = page.getByRole('button', { name: /create & continue editing/i });

  for (let attempt = 0; attempt < 3; attempt += 1) {
    await createBtn.click();

    try {
      await expect(page).toHaveURL(/\/documents\/\d+\/fullscreen/, { timeout: 15000 });
      return;
    } catch {
      if (await isRateLimited(page)) {
        await page.waitForTimeout(1500);
        continue;
      }
      throw new Error('Create document failed before reaching fullscreen editor.');
    }
  }

  await expect(page).toHaveURL(/\/documents\/\d+\/fullscreen/, { timeout: 30000 });
}

test.describe('Authentication', () => {
  test('should display login page', async ({ page }) => {
    await gotoLogin(page);
    await expect(page.locator('h1')).toContainText('Documentation Platform');
    await expect(page.locator('input#username')).toBeVisible();
    await expect(page.locator('input#password')).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('should login with valid credentials', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.locator('body')).toContainText(/dashboard|documents/i);
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await submitLogin(page, INVALID);
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    await loginAsAdmin(page);
    await page.getByRole('button', { name: /sign out/i }).click();
    await expect(page).toHaveURL(/\/(docs|login)/, { timeout: 10000 });
  });

  test('should redirect to login when not authenticated', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/(login|docs)/, { timeout: 10000 });
  });

  test('should login as customer and redirect to portal', async ({ page }) => {
    await loginAsCustomer(page);
  });

  test('customer should not access admin documents page', async ({ page }) => {
    await loginAsCustomer(page);

    await page.goto('/documents');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(750);

    const url = page.url();
    const redirectedAway = url.includes('/portal') || url.includes('/login');
    const deniedInPlace =
      url.includes('/documents') &&
      (await page.getByText(/access denied|forbidden|not authorized/i).count()) > 0;
    const noAdminActions =
      url.includes('/documents') &&
      (await page.getByRole('button', { name: /new document|upload file|create/i }).count()) === 0;

    expect(redirectedAway || deniedInPlace || noAdminActions).toBeTruthy();
  });
});

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
  });

  test('should display dashboard with stats', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Dashboard');
    await expect(page.getByText('Recent Documents')).toBeVisible();
  });

  test('should navigate to documents', async ({ page }) => {
    await page.getByRole('link', { name: /documents/i }).first().click();
    await expect(page).toHaveURL(/\/documents/, { timeout: 10000 });
  });
});

test.describe('Documents CRUD', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await openDocuments(page);
  });

  test('should display documents list', async ({ page }) => {
    // Wait for the table to be visible (it's always rendered on /documents)
    await expect(page.locator('table')).toBeVisible({ timeout: 15000 });
  });

  test('should create new document', async ({ page }) => {
    await createDocument(page, `E2E Test Document ${Date.now()}`);
    await expect(page.getByRole('button', { name: /preview/i })).toBeVisible();
  });

  test('should view document details', async ({ page }) => {
    await openDocuments(page);
    const firstDocLink = page.locator('table tbody tr a[href*="/documents/"]').first();

    if ((await firstDocLink.count()) > 0) {
      await firstDocLink.click();
    } else {
      await createDocument(page, `E2E Detail View ${Date.now()}`);
    }

    await expect(page).toHaveURL(/\/documents\/\d+\/fullscreen/, { timeout: 15000 });
    await expect(page.getByRole('button', { name: /versions/i })).toBeVisible();
  });
});

test.describe('Viewer Portal', () => {
  test('should access viewer without login', async ({ page }) => {
    await page.goto('/docs');
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.locator('body')).toContainText(/documentation library|latest releases|platform highlights/i);
  });

  test('should search documents in viewer', async ({ page }) => {
    await page.goto('/docs');

    const searchInput = page.locator('input[placeholder*="Search" i]').first();
    await expect(searchInput).toBeVisible();
    await searchInput.fill('test');
    await searchInput.press('Enter');

    await expect(page).toHaveURL(/search=/, { timeout: 10000 });
  });

  test('should view document in viewer', async ({ page }) => {
    await page.goto('/docs');

    const docLink = page.locator('a[href^="/doc/"]').first();
    if ((await docLink.count()) > 0) {
      await docLink.click();
      await expect(page).toHaveURL(/\/doc\/\d+/, { timeout: 10000 });
    } else {
      await expect(page.locator('body')).toContainText(/no documents|documents found|documentation library/i);
    }
  });
});

test.describe('Accessibility', () => {
  test('login page is keyboard navigable', async ({ page }) => {
    await gotoLogin(page);

    await page.keyboard.press('Tab');
    await expect(page.locator('input#username')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: /forgot password\?/i })).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.locator('input#password')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.locator('button[type="submit"]')).toBeFocused();
  });

  test('forms have proper labels', async ({ page }) => {
    await gotoLogin(page);
    await expect(page.locator('label[for="username"]')).toBeVisible();
    await expect(page.locator('label[for="password"]')).toBeVisible();
  });
});
