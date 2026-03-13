export interface DocumentSnippet {
  id: string
  label: string
  html: string
}

export const documentSnippets: DocumentSnippet[] = [
  {
    id: 'standard-header',
    label: 'Standard Header',
    html: `<h2>Summary</h2><p>Provide a concise summary for readers.</p>`,
  },
  {
    id: 'legal-notice',
    label: 'Legal Notice',
    html: `<blockquote><p>This material is confidential and intended only for authorized recipients.</p></blockquote>`,
  },
  {
    id: 'support-footer',
    label: 'Support Footer',
    html: `<p><strong>Need help?</strong> Contact the support team and include the document number, environment, and a short description of the issue.</p>`,
  },
  {
    id: 'change-log',
    label: 'Change Log',
    html: `<h2>Change Log</h2><ul><li><strong>Date:</strong> YYYY-MM-DD - <em>Describe the change</em></li></ul>`,
  },
]
