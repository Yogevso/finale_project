import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { isValidElement, type ReactElement, type ReactNode } from 'react'
import { Link, MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { parseDocumentHtml } from '@/lib/documentRenderer'

function findElement(
  node: ReactNode,
  predicate: (element: ReactElement<{ children?: ReactNode }>) => boolean,
): ReactElement<{ children?: ReactNode }> | null {
  if (Array.isArray(node)) {
    for (const child of node) {
      const match = findElement(child, predicate)
      if (match) {
        return match
      }
    }
    return null
  }

  if (!isValidElement<{ children?: ReactNode }>(node)) {
    return null
  }

  if (predicate(node)) {
    return node
  }

  return findElement(node.props.children, predicate)
}

describe('parseDocumentHtml', () => {
  it('renders code blocks with syntax highlighting output', () => {
    const { container } = render(
      <MemoryRouter>
        {parseDocumentHtml('<pre><code class="language-ts">const answer = 42;</code></pre>')}
      </MemoryRouter>,
    )

    const codeBlock = container.querySelector('.document-code-block')
    expect(codeBlock).not.toBeNull()
    expect(codeBlock).toHaveTextContent('const answer = 42;')
    expect(codeBlock?.querySelector('pre')).not.toBeNull()
  })

  it('wraps tables in a horizontal scroll container', () => {
    const { container } = render(
      <MemoryRouter>
        {parseDocumentHtml('<table><tbody><tr><td>Cell</td></tr></tbody></table>')}
      </MemoryRouter>,
    )

    expect(container.querySelector('.document-table-scroll > table')).not.toBeNull()
  })

  it('preserves extracted table wrappers without nesting duplicate scroll containers', () => {
    const { container } = render(
      <MemoryRouter>
        {parseDocumentHtml(
          '<div class="table-wrapper"><table class="extracted-table"><tbody><tr><td>Cell</td></tr></tbody></table></div>',
        )}
      </MemoryRouter>,
    )

    expect(container.querySelector('.table-wrapper.document-table-scroll > table.extracted-table')).not.toBeNull()
    expect(container.querySelectorAll('.document-table-scroll').length).toBe(1)
  })

  it('applies lazy image loading attributes', () => {
    render(
      <MemoryRouter>
        {parseDocumentHtml('<img src="/files/diagram.png" alt="Diagram" />')}
      </MemoryRouter>,
    )

    const image = screen.getByAltText('Diagram')
    expect(image).toHaveAttribute('loading', 'lazy')
    expect(image).toHaveAttribute('decoding', 'async')
  })

  it('opens extracted images in a lightbox using the figure caption as the title', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        {parseDocumentHtml(
          '<figure class="extracted-image"><img src="/files/diagram.png" alt="Diagram" /><figcaption class="extracted-image-caption">Architecture diagram</figcaption></figure>',
        )}
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: 'Diagram' }))

    const dialog = screen.getByRole('dialog', { name: 'Diagram' })
    expect(dialog).toBeInTheDocument()
    expect(dialog).toHaveTextContent('Architecture diagram')
  })

  it('adds target and rel to external links', () => {
    render(
      <MemoryRouter>
        {parseDocumentHtml('<a href="https://example.com/guide">Guide</a>')}
      </MemoryRouter>,
    )

    const link = screen.getByRole('link', { name: 'Guide' })
    expect(link).toHaveAttribute('href', 'https://example.com/guide')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('converts internal document links to router Link elements', () => {
    const parsed = parseDocumentHtml('<a href="/documents/123?tab=history#v2">Document</a>')
    const routerLink = findElement(
      parsed,
      (element) => element.type === Link,
    )
    const routerLinkWithTo =
      routerLink as ReactElement<{ children?: ReactNode; to?: string }> | null

    expect(routerLinkWithTo).not.toBeNull()
    expect(routerLinkWithTo?.props.to).toBe('/documents/123?tab=history#v2')
  })

  it('strips script tags and unsafe attributes before parsing', () => {
    const { container } = render(
      <MemoryRouter>
        {parseDocumentHtml(
          '<script>alert(1)</script><img src="javascript:alert(1)" onerror="alert(1)" alt="Unsafe" /><a href="javascript:alert(1)">Bad link</a><p>Safe text</p>',
        )}
      </MemoryRouter>,
    )

    expect(container.querySelector('script')).toBeNull()

    const image = screen.getByAltText('Unsafe')
    expect(image).not.toHaveAttribute('src')
    expect(image).not.toHaveAttribute('onerror')

    const unsafeLink = screen.getByText('Bad link').closest('a')
    expect(unsafeLink).not.toHaveAttribute('href')

    expect(screen.getByText('Safe text')).toBeInTheDocument()
  })

  it('keeps extracted article wrappers and speaker notes semantics', () => {
    const { container } = render(
      <MemoryRouter>
        {parseDocumentHtml(
          '<article class="docx-document" role="article"><h1>Intro</h1></article><details class="speaker-notes"><summary aria-expanded="false">Speaker Notes</summary><div class="notes-content"><p>Notes here</p></div></details>',
        )}
      </MemoryRouter>,
    )

    expect(container.querySelector('article.docx-document')).not.toBeNull()
    expect(container.querySelector('details.speaker-notes')).not.toBeNull()
    expect(screen.getByText('Speaker Notes')).toBeInTheDocument()
    expect(screen.getByText('Notes here')).toBeInTheDocument()
  })
})
