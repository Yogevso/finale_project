import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';
import { getApiAuthHeaders, loginByApi } from './helpers/auth';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DOCX_FIXTURE_PATH = path.resolve(
  __dirname,
  '../../backend/tests/fixtures/documents/wave_y_rich.docx',
);
const ADMIN_CREDENTIALS = { username: 'admin', password: 'admin123' };
const DOCX_MIME_TYPE =
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

test.describe('Office upload preview', () => {
  test.beforeEach(async ({ page }) => {
    await loginByApi(page, ADMIN_CREDENTIALS, /\/(dashboard|documents)/, '/dashboard');
  });

  test('uploads a DOCX fixture and renders extracted headings, tables, and images', async ({
    page,
  }) => {
    const headers = await getApiAuthHeaders(page, ADMIN_CREDENTIALS);
    const fileBuffer = await fs.readFile(DOCX_FIXTURE_PATH);
    const uploadTitle = `Wave Y Upload ${Date.now()}`;

    const uploadResponse = await page.request.post('/api/v1/documents/upload', {
      headers,
      multipart: {
        file: {
          name: path.basename(DOCX_FIXTURE_PATH),
          mimeType: DOCX_MIME_TYPE,
          buffer: fileBuffer,
        },
        title: uploadTitle,
        description: 'Playwright DOCX upload fixture',
        category: 'Testing',
        visibility: 'internal',
        status: 'draft',
      },
    });

    expect(uploadResponse.ok()).toBeTruthy();
    const uploadedDocument = (await uploadResponse.json()) as { id: number };

    await page.goto(`/documents/${uploadedDocument.id}/fullscreen`);

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
    await expect(preview.locator('figure.extracted-image img')).toBeVisible();
    await expect(preview).toContainText('Upload DOCX through the management UI');
    await expect(preview).toContainText('Verify semantic headings and lists');
  });
});
