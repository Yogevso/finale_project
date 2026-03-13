import { createElement, type ReactNode } from 'react'
import parse, {
  attributesToProps,
  domToReact,
  Element,
  type DOMNode,
  type HTMLReactParserOptions,
} from 'html-react-parser'
import type { ChildNode } from 'domhandler'
import { Link } from 'react-router-dom'
import DocumentCodeBlock from '@/components/DocumentCodeBlock'
import LightboxImage from '@/components/LightboxImage'
import { getWindowLocation } from '@/env/dom'
import { sanitizeHtmlForPreview } from '@/lib/htmlSanitizer'

interface DocumentRendererReplaceContext {
  renderChildren: (nodes: DOMNode[]) => ReactNode
}

type ParserReplaceResult = ReturnType<NonNullable<HTMLReactParserOptions['replace']>>

export type DocumentHtmlReplace = (
  domNode: DOMNode,
  index: number,
  context: DocumentRendererReplaceContext,
) => ParserReplaceResult

interface ParseDocumentHtmlOptions {
  replace?: DocumentHtmlReplace
}

const CODE_LANGUAGE_ALIASES: Record<string, string> = {
  cjs: 'javascript',
  css: 'css',
  html: 'markup',
  js: 'javascript',
  json: 'json',
  jsx: 'jsx',
  md: 'markdown',
  plaintext: 'text',
  py: 'python',
  rb: 'ruby',
  shell: 'bash',
  sh: 'bash',
  sql: 'sql',
  svg: 'markup',
  text: 'text',
  ts: 'typescript',
  tsx: 'tsx',
  xml: 'markup',
  yml: 'yaml',
}

function isElementNode(node: DOMNode | ChildNode): node is Element {
  return node.type === 'tag'
}

function toDomNodes(nodes: Element['children']): DOMNode[] {
  return nodes as unknown as DOMNode[]
}

function getTextContent(nodes: DOMNode[]): string {
  return nodes
    .map((node) => {
      if (node.type === 'text') {
        return node.data
      }
      if (isElementNode(node)) {
        return getTextContent(toDomNodes(node.children))
      }
      return ''
    })
    .join('')
}

function normalizeLanguageToken(token: string | undefined): string | null {
  if (!token) {
    return null
  }

  const normalized = token.trim().toLowerCase()
  if (!normalized) {
    return null
  }

  return CODE_LANGUAGE_ALIASES[normalized] || normalized
}

function detectCodeLanguage(className: string, codeText: string): string {
  const classTokens = className
    .split(/\s+/)
    .map((token) => token.trim())
    .filter(Boolean)

  for (const token of classTokens) {
    const match = token.match(/^(?:language|lang)-([a-z0-9#+-]+)$/i)
    const aliasCandidate = Object.prototype.hasOwnProperty.call(CODE_LANGUAGE_ALIASES, token)
      ? token
      : undefined
    const normalized = normalizeLanguageToken(match?.[1] || aliasCandidate)
    if (normalized) {
      return normalized
    }
  }

  const trimmedCode = codeText.trim()
  if (!trimmedCode) {
    return 'text'
  }

  if (/^\s*</.test(trimmedCode) && /<\/?[a-z][\s\S]*>/i.test(trimmedCode)) {
    return 'markup'
  }
  if (/(^|\n)\s*(interface|type)\s+\w+/.test(trimmedCode) || /:\s*[A-Z][A-Za-z0-9_<>,[\]? ]+$/.test(trimmedCode)) {
    return 'typescript'
  }
  if (/(^|\n)\s*(const|let|var|import|export)\s+/.test(trimmedCode) || /=>/.test(trimmedCode)) {
    return trimmedCode.includes('<') ? 'tsx' : 'javascript'
  }
  if (/(^|\n)\s*def\s+\w+\s*\(/.test(trimmedCode) || /(^|\n)\s*from\s+\w+\s+import\s+/.test(trimmedCode)) {
    return 'python'
  }
  if (/(^|\n)\s*(SELECT|INSERT|UPDATE|DELETE|WITH)\b/i.test(trimmedCode)) {
    return 'sql'
  }
  if (
    trimmedCode.startsWith('#!/bin/') ||
    /(^|\n)\s*(npm |yarn |pnpm |git )/.test(trimmedCode)
  ) {
    return 'bash'
  }
  if (/^\s*(?:\[|\{)/.test(trimmedCode) && /[:}]/.test(trimmedCode)) {
    return 'json'
  }

  return 'text'
}

function resolveInternalDocumentPath(href: string): string | null {
  const trimmedHref = href.trim()
  if (!trimmedHref) {
    return null
  }

  try {
    const parsedUrl = new URL(trimmedHref, getWindowLocation().origin)
    if (
      parsedUrl.origin === getWindowLocation().origin &&
      parsedUrl.pathname.startsWith('/documents/')
    ) {
      return `${parsedUrl.pathname}${parsedUrl.search}${parsedUrl.hash}`
    }
  } catch {
    if (trimmedHref.startsWith('/documents/')) {
      return trimmedHref
    }
  }

  return trimmedHref.startsWith('/documents/') ? trimmedHref : null
}

function isExternalHttpLink(href: string): boolean {
  try {
    const parsedUrl = new URL(href, getWindowLocation().origin)
    return (
      (parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:') &&
      parsedUrl.origin !== getWindowLocation().origin
    )
  } catch {
    return false
  }
}

function replaceCodeBlock(node: Element): ParserReplaceResult {
  if (node.name !== 'pre') {
    return undefined
  }

  const codeChild = node.children.find(
    (child): child is Element => isElementNode(child) && child.name === 'code',
  )
  const codeText = getTextContent(
    toDomNodes(codeChild?.children ?? node.children),
  ).replace(/\n$/, '')
  const className = [node.attribs.class, codeChild?.attribs.class].filter(Boolean).join(' ')
  const language = detectCodeLanguage(className, codeText)

  return (
    <DocumentCodeBlock
      code={codeText}
      language={language}
      className={className || undefined}
    />
  )
}

function replaceTable(
  node: Element,
  parserOptions: HTMLReactParserOptions,
): ParserReplaceResult {
  if (node.name !== 'table') {
    return undefined
  }

  const parent = node.parent
  if (parent && isElementNode(parent) && hasClassName(parent, 'table-wrapper')) {
    return createElement(
      'table',
      attributesToProps(node.attribs),
      domToReact(toDomNodes(node.children), parserOptions),
    )
  }

  return (
    <div className="document-table-scroll">
      {createElement(
        'table',
        attributesToProps(node.attribs),
        domToReact(toDomNodes(node.children), parserOptions),
      )}
    </div>
  )
}

function replaceImage(node: Element): ParserReplaceResult {
  if (node.name !== 'img') {
    return undefined
  }

  const parent = node.parent
  const figureCaption =
    parent && isElementNode(parent) && parent.name === 'figure'
      ? parent.children.find(
          (child): child is Element => isElementNode(child) && child.name === 'figcaption',
        )
      : null
  const derivedTitle = figureCaption
    ? getTextContent(toDomNodes(figureCaption.children)).trim() || undefined
    : undefined

  return (
    <LightboxImage
      {...attributesToProps(node.attribs)}
      title={
        typeof node.attribs.title === 'string' && node.attribs.title.trim()
          ? node.attribs.title
          : derivedTitle
      }
    />
  )
}

function replaceTableWrapper(
  node: Element,
  parserOptions: HTMLReactParserOptions,
): ParserReplaceResult {
  if (node.name !== 'div' || !hasClassName(node, 'table-wrapper')) {
    return undefined
  }

  return createElement(
    'div',
    {
      ...attributesToProps(node.attribs),
      className: [node.attribs.class, 'document-table-scroll'].filter(Boolean).join(' '),
      tabIndex: 0,
    },
    domToReact(toDomNodes(node.children), parserOptions),
  )
}

function replaceLink(
  node: Element,
  parserOptions: HTMLReactParserOptions,
): ParserReplaceResult {
  if (node.name !== 'a') {
    return undefined
  }

  const props = attributesToProps(node.attribs)
  const children = domToReact(toDomNodes(node.children), parserOptions)
  const href = typeof node.attribs.href === 'string' ? node.attribs.href : ''

  if (!href) {
    return createElement('a', props, children)
  }

  const internalDocumentPath = resolveInternalDocumentPath(href)
  if (internalDocumentPath) {
    const linkProps = { ...props }
    delete linkProps.href
    return (
      <Link {...linkProps} to={internalDocumentPath}>
        {children}
      </Link>
    )
  }

  if (isExternalHttpLink(href)) {
    return createElement(
      'a',
      {
        ...props,
        href,
        rel: 'noopener noreferrer',
        target: '_blank',
      },
      children,
    )
  }

  return createElement('a', { ...props, href }, children)
}

function buildParserOptions(customReplace?: DocumentHtmlReplace): HTMLReactParserOptions {
  const parserOptions: HTMLReactParserOptions = {
    replace(domNode, index) {
      const context: DocumentRendererReplaceContext = {
        renderChildren: (nodes) => domToReact(nodes, parserOptions),
      }

      if (isElementNode(domNode)) {
        const builtInReplacement =
          replaceCodeBlock(domNode) ??
          replaceTableWrapper(domNode, parserOptions) ??
          replaceTable(domNode, parserOptions) ??
          replaceImage(domNode) ??
          replaceLink(domNode, parserOptions)

        if (builtInReplacement !== undefined) {
          return builtInReplacement
        }
      }

      return customReplace?.(domNode, index, context)
    },
  }

  return parserOptions
}

function hasClassName(node: Element, className: string): boolean {
  return (node.attribs.class || '')
    .split(/\s+/)
    .map((token) => token.trim())
    .filter(Boolean)
    .includes(className)
}

export function parseDocumentHtml(
  html: string,
  options?: ParseDocumentHtmlOptions,
): ReactNode {
  const sanitizedHtml = sanitizeHtmlForPreview(html || '')
  return parse(sanitizedHtml, buildParserOptions(options?.replace))
}
