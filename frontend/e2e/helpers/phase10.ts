import { expect, type Locator, type Page } from '@playwright/test';

export const RESPONSIVE_VIEWPORTS = [
  { width: 375, height: 812, label: 'mobile-375' },
  { width: 768, height: 1024, label: 'tablet-768' },
  { width: 1024, height: 768, label: 'desktop-1024' },
  { width: 1440, height: 1024, label: 'desktop-1440' },
] as const;

export async function stabilizeUi(page: Page) {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.addStyleTag({
    content: `
      *,
      *::before,
      *::after {
        animation: none !important;
        transition: none !important;
        caret-color: transparent !important;
        scroll-behavior: auto !important;
      }
      [data-sonner-toaster],
      [data-radix-popper-content-wrapper] {
        animation: none !important;
      }
    `,
  });
}

export async function waitForAppReady(page: Page, readyTarget?: Locator | string) {
  await page.waitForLoadState('domcontentloaded');

  if (readyTarget) {
    if (typeof readyTarget === 'string') {
      await expect(page.locator(readyTarget).first()).toBeVisible({ timeout: 15000 });
    } else {
      await expect(readyTarget).toBeVisible({ timeout: 15000 });
    }
  }

  await page.waitForLoadState('networkidle').catch(() => undefined);
  await page.waitForTimeout(200);
  await stabilizeUi(page);
}

export async function expectNoHorizontalOverflow(page: Page) {
  const overflowing = await page.evaluate(() => {
    return Array.from(document.querySelectorAll<HTMLElement>('body *'))
      .map((element) => {
        const rect = element.getBoundingClientRect();
        if (rect.right > window.innerWidth + 4) {
          return `${element.tagName}.${element.className}`.trim();
        }
        return null;
      })
      .filter((value): value is string => Boolean(value))
      .slice(0, 10);
  });

  expect(
    overflowing,
    `Expected no horizontal overflow, but found: ${overflowing.join(', ')}`,
  ).toEqual([]);
}

export function assertNoBlockingViolations(
  violations: Array<{ impact?: string | null; id: string; description: string; nodes: unknown[] }>,
) {
  const blocking = violations.filter((violation) =>
    violation.impact === 'critical' || violation.impact === 'serious',
  );

  expect(
    blocking,
    blocking.length
      ? `Blocking accessibility violations:\n${blocking
          .map(
            (violation) =>
              `[${violation.impact}] ${violation.id}: ${violation.description} (${violation.nodes.length} node(s))`,
          )
          .join('\n')}`
      : undefined,
  ).toEqual([]);
}

