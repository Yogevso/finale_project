import type { Step } from 'react-joyride'

export const documentsPageTour: Step[] = [
  {
    target: '[data-tour="documents-search-bar"]',
    title: 'Search fast',
    content: 'Use this search bar to quickly find documents by title or number.',
    disableBeacon: true,
  },
  {
    target: '[data-tour="documents-filter-panel"]',
    title: 'Filter results',
    content: 'Use status and visibility filters to narrow down the list.',
  },
  {
    target: '[data-tour="documents-create-button"]',
    title: 'Create document',
    content: 'Start drafting a new document from here.',
  },
]

export const documentDetailTour: Step[] = [
  {
    target: '[data-tour="document-toc-panel"]',
    title: 'TOC panel',
    content: 'Jump across sections quickly using the table of contents.',
    disableBeacon: true,
  },
  {
    target: '[data-tour="document-preview-toolbar"]',
    title: 'Preview toolbar',
    content: 'Switch preview modes and attachments from this toolbar.',
  },
  {
    target: '[data-tour="document-inline-comment-area"]',
    title: 'Inline comments',
    content: 'Select text in the preview and add inline comments for collaborators.',
  },
]
