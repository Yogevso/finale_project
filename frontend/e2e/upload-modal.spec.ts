import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { loginByApi } from './helpers/auth';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DOCX_FIXTURE_PATH = path.resolve(
  __dirname,
  '../../backend/tests/fixtures/documents/wave_y_rich.docx',
);
const ADMIN_CREDENTIALS = { username: 'admin', password: 'admin123' };
const DOCX_MIME_TYPE =
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const INVALID_PDF_BUFFER = Buffer.from('%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF');

async function openUploadModal(page: Page) {
  await page.goto('/documents');
  await page.getByRole('button', { name: /upload file/i }).click();
  await expect(page.getByRole('heading', { name: /upload document/i })).toBeVisible();
}

test.describe('Upload modal UI flow', () => {
  test.beforeEach(async ({ page }) => {
    await loginByApi(page, ADMIN_CREDENTIALS, /\/(dashboard|documents)/, '/documents');
  });

  test('uploads a DOCX fixture through the modal and opens fullscreen preview', async ({ page }) => {
    test.slow();

    const uploadTitle = `Wave Y Modal Upload ${Date.now()}`;
    const fileBuffer = await fs.readFile(DOCX_FIXTURE_PATH);

    await openUploadModal(page);

    await page.getByTestId('primary-upload-input').setInputFiles({
      name: path.basename(DOCX_FIXTURE_PATH),
      mimeType: DOCX_MIME_TYPE,
      buffer: fileBuffer,
    });
    await page.getByLabel('Initial Status').selectOption('approved');
    await page.getByLabel('Title').fill(uploadTitle);
    await page.getByRole('button', { name: /^upload$/i }).click();

    await page.waitForURL(/\/documents\/\d+\/fullscreen/, { timeout: 60000 });

    const readerViewButton = page.getByRole('button', { name: /reader view/i });
    if (await readerViewButton.isVisible().catch(() => false)) {
      await readerViewButton.click();
    }

    const preview = page.locator('#document-content-area');
    await expect(
      preview.getByRole('heading', { name: 'Wave Y Extractor Fixture' }),
    ).toBeVisible({ timeout: 60000 });
    await expect(preview.getByRole('heading', { name: 'Release Overview' })).toBeVisible();
    await expect(preview.locator('.table-wrapper table.extracted-table')).toBeVisible();
  });

  test('shows client validation when a PDF is selected in the modal', async ({ page }) => {
    await openUploadModal(page);

    await page.getByTestId('primary-upload-input').setInputFiles({
      name: 'legacy.pdf',
      mimeType: 'application/pdf',
      buffer: INVALID_PDF_BUFFER,
    });

    await expect(page.getByText('Only DOCX and PPTX files are allowed')).toBeVisible();
    await expect(page.getByRole('button', { name: /^upload$/i })).toBeDisabled();
  });

  test('disables closing the modal while the upload request is in flight', async ({ page }) => {
    test.slow();

    const fileBuffer = await fs.readFile(DOCX_FIXTURE_PATH);
    const uploadRoutePattern = '**/api/v1/documents/upload';
    await page.route(uploadRoutePattern, async (route) => {
      await page.waitForTimeout(1200);
      await route.continue();
    });

    await openUploadModal(page);

    await page.getByTestId('primary-upload-input').setInputFiles({
      name: path.basename(DOCX_FIXTURE_PATH),
      mimeType: DOCX_MIME_TYPE,
      buffer: fileBuffer,
    });
    await page.getByRole('button', { name: /^upload$/i }).click();

    await expect(page.getByRole('button', { name: /cancel/i })).toBeDisabled();
    await expect(page.getByRole('progressbar', { name: /upload progress/i })).toBeVisible();

    await page.waitForURL(/\/documents\/\d+\/fullscreen/, { timeout: 60000 });
    await page.unroute(uploadRoutePattern);
  });
});
