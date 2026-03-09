import { describe, expect, it } from 'vitest'
import { sanitizeHtmlForPreview } from '@/lib/htmlSanitizer'

describe('sanitizeHtmlForPreview', () => {
  it('strips script tags and unsafe attributes while preserving safe content', () => {
    const sanitized = sanitizeHtmlForPreview(
      '<script>alert(1)</script><p onclick="evil()">Hello</p><img src="javascript:alert(1)" onerror="alert(1)" alt="Unsafe" /><a href="javascript:alert(1)">Bad link</a><a href="https://example.com/docs">Safe link</a>',
    )

    expect(sanitized).not.toContain('<script')
    expect(sanitized).not.toContain('onclick=')
    expect(sanitized).not.toContain('onerror=')
    expect(sanitized).not.toContain('javascript:alert(1)')
    expect(sanitized).toContain('<p>Hello</p>')
    expect(sanitized).toContain('href="https://example.com/docs"')
  })
})
