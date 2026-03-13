const ALLOWED_TAGS = new Set([
  'a',
  'article',
  'b',
  'blockquote',
  'br',
  'caption',
  'code',
  'col',
  'colgroup',
  'del',
  'details',
  'div',
  'em',
  'figure',
  'figcaption',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'hr',
  'i',
  'img',
  'li',
  'ol',
  'p',
  'pre',
  's',
  'section',
  'span',
  'strong',
  'sub',
  'summary',
  'sup',
  'table',
  'tbody',
  'td',
  'tfoot',
  'th',
  'thead',
  'tr',
  'u',
  'ul',
])

const DROP_TAGS = new Set([
  'script',
  'style',
  'iframe',
  'object',
  'embed',
  'link',
  'meta',
  'form',
  'input',
  'textarea',
  'button',
  'select',
  'option',
])

const GLOBAL_ATTRIBUTES = new Set([
  'aria-expanded',
  'aria-label',
  'class',
  'data-page',
  'data-slide-count',
  'data-slide-number',
  'id',
  'role',
])
const PER_TAG_ATTRIBUTES: Record<string, Set<string>> = {
  a: new Set(['href', 'title', 'target', 'rel']),
  img: new Set(['src', 'alt', 'title', 'width', 'height']),
  table: new Set(['summary']),
  th: new Set(['colspan', 'rowspan', 'scope']),
  td: new Set(['colspan', 'rowspan']),
  col: new Set(['span', 'width']),
  colgroup: new Set(['span', 'width']),
}

const SAFE_LINK_PROTOCOLS = ['http:', 'https:', 'mailto:', 'tel:']
const CALLOUT_CLASS_VARIANTS: Record<'info' | 'warning' | 'tip' | 'danger', string[]> = {
  info: ['callout', 'callout-info', 'callout-note', 'info', 'note', 'alert', 'notice'],
  warning: ['callout-warning', 'warning', 'warn', 'caution', 'alert-warning'],
  tip: ['callout-tip', 'tip', 'hint', 'success', 'pro-tip'],
  danger: ['callout-danger', 'danger', 'error', 'critical', 'alert-danger'],
}

function isSafeHref(value: string): boolean {
  const trimmed = value.trim()
  if (!trimmed) return false
  if (
    trimmed.startsWith('/') ||
    trimmed.startsWith('./') ||
    trimmed.startsWith('../') ||
    trimmed.startsWith('#')
  ) {
    return true
  }
  try {
    const parsed = new URL(trimmed, window.location.origin)
    return SAFE_LINK_PROTOCOLS.includes(parsed.protocol)
  } catch {
    return false
  }
}

function isSafeImageSrc(value: string): boolean {
  const trimmed = value.trim()
  if (!trimmed) return false
  if (
    trimmed.startsWith('/') ||
    trimmed.startsWith('./') ||
    trimmed.startsWith('../') ||
    trimmed.startsWith('blob:')
  ) {
    return true
  }
  if (/^data:image\/(?:png|jpe?g|gif|webp|svg\+xml);base64,[a-z0-9+/=\s]+$/i.test(trimmed)) {
    return true
  }
  try {
    const parsed = new URL(trimmed, window.location.origin)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

function sanitizeNumericAttribute(element: Element, name: string): void {
  const raw = element.getAttribute(name)
  if (!raw) return
  const parsed = Number.parseInt(raw, 10)
  if (!Number.isFinite(parsed) || parsed <= 0) {
    element.removeAttribute(name)
    return
  }
  element.setAttribute(name, String(parsed))
}

function normalizeClassAttribute(tagName: string, value: string): string | null {
  const normalizedTokens = value
    .split(/\s+/)
    .map((item) => item.trim())
    .filter((item) => /^[a-z0-9_-]+$/i.test(item))

  if (normalizedTokens.length === 0) {
    return null
  }

  const canBeCallout = tagName === 'div' || tagName === 'p' || tagName === 'blockquote'
  if (!canBeCallout) {
    return normalizedTokens.join(' ')
  }

  const variant = (
    Object.entries(CALLOUT_CLASS_VARIANTS) as Array<
      [keyof typeof CALLOUT_CLASS_VARIANTS, string[]]
    >
  ).find(([, candidates]) =>
    normalizedTokens.some((token) =>
      candidates.some((candidate) => token === candidate || token.includes(candidate)),
    ),
  )?.[0]

  if (!variant) {
    return normalizedTokens.join(' ')
  }

  const calloutTokens = new Set(Object.values(CALLOUT_CLASS_VARIANTS).flat())
  const filteredTokens = normalizedTokens.filter((token) => !calloutTokens.has(token))
  const nextTokens = [...filteredTokens, `callout-${variant}`]
  return Array.from(new Set(nextTokens)).join(' ')
}

function unwrapElement(element: Element): void {
  const parent = element.parentNode
  if (!parent) return
  while (element.firstChild) {
    parent.insertBefore(element.firstChild, element)
  }
  parent.removeChild(element)
}

function sanitizeAttributes(element: Element): void {
  const tagName = element.tagName.toLowerCase()
  const allowedForTag = PER_TAG_ATTRIBUTES[tagName] || new Set<string>()
  const attributes = Array.from(element.attributes)

  attributes.forEach((attribute) => {
    const name = attribute.name.toLowerCase()
    const value = attribute.value

    if (name.startsWith('on') || name === 'style') {
      element.removeAttribute(attribute.name)
      return
    }

    if (!(GLOBAL_ATTRIBUTES.has(name) || allowedForTag.has(name))) {
      element.removeAttribute(attribute.name)
      return
    }

    if (name === 'class') {
      const normalizedClass = normalizeClassAttribute(tagName, value)
      if (!normalizedClass) {
        element.removeAttribute(attribute.name)
      } else {
        element.setAttribute('class', normalizedClass)
      }
      return
    }

    if (name === 'id') {
      const normalizedId = value.trim()
      if (!/^[a-z0-9][a-z0-9:_-]*$/i.test(normalizedId)) {
        element.removeAttribute(attribute.name)
      } else {
        element.setAttribute('id', normalizedId)
      }
      return
    }

    if (tagName === 'a' && name === 'href' && !isSafeHref(value)) {
      element.removeAttribute(attribute.name)
      return
    }

    if (tagName === 'img' && name === 'src' && !isSafeImageSrc(value)) {
      element.removeAttribute(attribute.name)
      return
    }

    if (
      name === 'data-page' ||
      name === 'data-slide-count' ||
      name === 'data-slide-number' ||
      name === 'colspan' ||
      name === 'rowspan' ||
      name === 'span' ||
      name === 'width' ||
      name === 'height'
    ) {
      sanitizeNumericAttribute(element, name)
      return
    }

    if (tagName === 'a' && name === 'target') {
      if (value !== '_blank' && value !== '_self') {
        element.removeAttribute('target')
      }
    }
  })

  if (tagName === 'a' && element.getAttribute('target') === '_blank') {
    element.setAttribute('rel', 'noopener noreferrer')
  }
}

function sanitizeElement(element: Element): void {
  const children = Array.from(element.children)
  children.forEach((child) => sanitizeElement(child))

  const tagName = element.tagName.toLowerCase()
  if (DROP_TAGS.has(tagName)) {
    element.remove()
    return
  }

  if (!ALLOWED_TAGS.has(tagName)) {
    unwrapElement(element)
    return
  }

  sanitizeAttributes(element)
}

export function sanitizeHtmlForPreview(html: string): string {
  const parser = new DOMParser()
  const doc = parser.parseFromString(html || '', 'text/html')
  Array.from(doc.body.children).forEach((child) => sanitizeElement(child))
  return doc.body.innerHTML
}
