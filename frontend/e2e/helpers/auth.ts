import { expect, type Page } from '@playwright/test';

type Credentials = {
  username: string;
  password: string;
};

type TokenPayload = {
  access_token: string;
  refresh_token?: string | null;
};

const tokenCache = new Map<string, TokenPayload>();
const E2E_BYPASS_HEADERS = { 'x-e2e-test': '1' };

function parseRetryAfterSeconds(headers: Record<string, string>, body: unknown): number {
  const retryHeader = Number(headers['retry-after'] ?? '');
  if (Number.isFinite(retryHeader) && retryHeader > 0) {
    return Math.ceil(retryHeader);
  }

  if (typeof body === 'object' && body !== null && 'retry_after' in body) {
    const retryBody = Number((body as { retry_after?: unknown }).retry_after ?? '');
    if (Number.isFinite(retryBody) && retryBody > 0) {
      return Math.ceil(retryBody);
    }
  }

  return 2;
}

async function requestTokens(page: Page, credentials: Credentials): Promise<TokenPayload> {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    let response;
    try {
      response = await page.request.post('/api/v1/auth/login', {
        data: credentials,
        headers: E2E_BYPASS_HEADERS,
        failOnStatusCode: false,
        timeout: 7000,
      });
    } catch (error) {
      if (attempt === 2) {
        throw error;
      }
      await page.waitForTimeout(1000 + attempt * 1000);
      continue;
    }

    const responseBody = (await response.json().catch(() => ({}))) as unknown;
    if (response.status() === 429) {
      const retryAfterSeconds = parseRetryAfterSeconds(response.headers(), responseBody);
      await page.waitForTimeout(retryAfterSeconds * 1000);
      continue;
    }

    if (!response.ok()) {
      throw new Error(`API login failed for "${credentials.username}" with status ${response.status()}.`);
    }

    const payload = responseBody as TokenPayload;
    if (!payload.access_token) {
      throw new Error(`API login for "${credentials.username}" did not return an access token.`);
    }
    return payload;
  }

  throw new Error(`API login retries exhausted for "${credentials.username}".`);
}

async function applyTokens(page: Page, payload: TokenPayload) {
  // Ensure auth state exists before app scripts boot on the next navigation.
  await page.addInitScript((tokens) => {
    localStorage.setItem('token', tokens.access_token);
    localStorage.setItem('access_token', tokens.access_token);
    if (tokens.refresh_token) {
      localStorage.setItem('refreshToken', tokens.refresh_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);
    } else {
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('refresh_token');
    }
    sessionStorage.setItem('viewer_landed', '1');
  }, payload);
}

export async function loginByApi(
  page: Page,
  credentials: Credentials,
  expectedUrl: RegExp,
  landingPath: string,
) {
  await page.setExtraHTTPHeaders(E2E_BYPASS_HEADERS);

  for (let attempt = 0; attempt < 4; attempt += 1) {
    const shouldForceTokenRefresh = attempt >= 1;
    let payload = tokenCache.get(credentials.username);
    if (!payload || shouldForceTokenRefresh) {
      payload = await requestTokens(page, credentials);
      tokenCache.set(credentials.username, payload);
    }

    await applyTokens(page, payload);
    await page.goto(landingPath, { waitUntil: 'domcontentloaded' });
    await page.waitForURL(
      /\/(login|dashboard|documents|portal|reviews|users|admin|settings|companies|notifications|audit)/,
      { timeout: 5000 },
    ).catch(() => undefined);

    if (expectedUrl.test(page.url())) {
      await page.waitForTimeout(300);
      if (!page.url().includes('/login')) {
        return;
      }
    }

    const rateLimited = await page.getByText(/too many requests|retry after|please try again later/i).first().isVisible().catch(() => false);
    if (page.isClosed()) {
      throw new Error(`Page closed while authenticating "${credentials.username}".`);
    }
    if (rateLimited) {
      await page.waitForTimeout(1000 + attempt * 500);
    } else {
      await page.waitForTimeout(500 + attempt * 300);
    }
  }

  if (expectedUrl.test(page.url()) && !page.url().includes('/login')) {
    return;
  }
  throw new Error(`Failed to authenticate "${credentials.username}" and reach ${expectedUrl}. Final URL: ${page.url()}`);
}
