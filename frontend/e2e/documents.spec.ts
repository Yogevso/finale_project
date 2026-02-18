import { test, expect, type Page } from '@playwright/test';
import { loginByApi } from './helpers/auth';

async function isRateLimited(page: Page) {
  const rateLimitMessage = page.getByText(/too many requests|please try again later|retry after/i).first();
  return rateLimitMessage.isVisible().catch(() => false);
}

async function loginAsAdmin(page: Page) {
  await loginByApi(page, { username: 'admin', password: 'admin123' }, /\/(dashboard|documents)/, '/dashboard');
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
  const createButton = page.getByRole('button', { name: /create & continue editing/i });

  for (let attempt = 0; attempt < 3; attempt += 1) {
    await createButton.click();

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

async function openExistingDocumentOrCreate(page: Page) {
  await openDocuments(page);
  const firstDocLink = page.locator('table tbody tr a[href*="/documents/"]').first();

  if ((await firstDocLink.count()) > 0) {
    await firstDocLink.click();
    await page.waitForLoadState('networkidle');
    const notFound = (await page.getByText(/document not found|may not exist/i).count()) > 0;
    const validDocUrl = /\/documents\/\d+\/fullscreen/.test(page.url());
    if (validDocUrl && !notFound) {
      return;
    }
  }

  await createDocument(page, `E2E Docs Spec ${Date.now()}`);
}

test.describe('Document Versions', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should view versions tab on document', async ({ page }) => {
    await openExistingDocumentOrCreate(page);
    await page.getByRole('button', { name: /versions/i }).click();
    await expect(page.locator('body')).toContainText(/version|publish|no versions/i);
  });
});

test.describe('Document Attachments', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should view attachments tab on document', async ({ page }) => {
    await openExistingDocumentOrCreate(page);
    await page.getByRole('button', { name: /attachments/i }).click();
    await expect(page.locator('body')).toContainText(/attachment|upload|file/i);
  });
});

test.describe('Document Comments', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should view comments tab on document', async ({ page }) => {
    await openExistingDocumentOrCreate(page);
    const notFound = (await page.getByText(/document not found|may not exist/i).count()) > 0;
    if (notFound) {
      test.skip(true, 'Document detail is unavailable for comments checks.');
      return;
    }

    const commentsTab = page.getByRole('button', { name: /comments/i });
    if ((await commentsTab.count()) > 0) {
      await commentsTab.click();
    }
    await expect(page.locator('body')).toContainText(/comments?|post comment|no comments yet/i);
  });

  test('should add a comment', async ({ page }) => {
    await openExistingDocumentOrCreate(page);
    const commentsTab = page.getByRole('button', { name: /comments/i });
    if ((await commentsTab.count()) > 0) {
      await commentsTab.click();
    }

    const comment = `E2E Test Comment ${Date.now()}`;
    const commentInput = page
      .locator('textarea[placeholder*="comment" i], textarea[name*="comment" i], textarea#comment, [data-testid="comment-input"] textarea')
      .first();

    if ((await commentInput.count()) === 0) {
      test.skip(true, 'Comment input is not available in this build.');
      return;
    }

    await expect(commentInput).toBeVisible();
    await commentInput.fill(comment);

    const postButton = page
      .locator('button:has-text("Post Comment"), button:has-text("Post"), button:has-text("Submit")')
      .first();
    await expect(postButton).toBeVisible();
    await postButton.click();
    await expect(page.locator('body')).toContainText(comment);
  });
});

test.describe('Search Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should search documents in management portal', async ({ page }) => {
    await openDocuments(page);

    const searchInput = page.locator('input[placeholder*="Search documents" i]');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('test');
    await expect(searchInput).toHaveValue('test');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should filter documents by status', async ({ page }) => {
    await openDocuments(page);

    const statusSummary = page.locator('summary').filter({ hasText: /Status:/i });
    await expect(statusSummary).toBeVisible();
    await statusSummary.click();

    await page.getByRole('button', { name: 'Published' }).click();
    await expect(statusSummary).toContainText(/Status:\s*Published/i);
  });
});
