import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import CustomerDocumentPage from '@/pages/portal/CustomerDocumentPage';

const mockGetDocument = vi.fn();
const mockGetRelatedDocuments = vi.fn();
const mockSubmitFeedback = vi.fn();
const mockUpdateReadingProgress = vi.fn();

vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    isCustomer: true,
    user: { id: 5, role: 'customer' },
  }),
}));

vi.mock('@/lib/portalApi', async () => {
  const actual = await vi.importActual<typeof import('@/lib/portalApi')>('@/lib/portalApi');
  return {
    ...actual,
    portalApi: {
      ...actual.portalApi,
      getDocument: (...args: unknown[]) => mockGetDocument(...args),
      getRelatedDocuments: (...args: unknown[]) => mockGetRelatedDocuments(...args),
      submitFeedback: (...args: unknown[]) => mockSubmitFeedback(...args),
      updateReadingProgress: (...args: unknown[]) => mockUpdateReadingProgress(...args),
    },
  };
});

vi.mock('@/pages/document-detail/components/FullscreenTopBar', () => ({
  FullscreenTopBar: () => null,
}));

function renderPage(initialEntry = '/portal/documents/7') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/portal/documents/:id" element={<CustomerDocumentPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const documentPayload = {
  id: 7,
  title: 'Customer Guide',
  description: 'Published instructions',
  content: `
    <h1>Overview heading in HTML</h1>
    <p>Welcome to the document.</p>
    <h2>Details heading in HTML</h2>
    <p>Important selected sentence for feedback.</p>
  `,
  category: 'Guides',
  topic: 'Setup',
  platform: 'Portal',
  release_branch: null,
  tags: ['alpha'],
  visibility: 'company',
  version: 2,
  created_at: '2026-03-28T10:00:00Z',
  updated_at: '2026-03-28T12:00:00Z',
  published_at: '2026-03-28T12:00:00Z',
  toc_items: [
    {
      id: 'toc-0',
      title: 'Internal TOC Intro',
      level: 1,
      page: 1,
      page_start: 1,
      page_end: 1,
      anchor_id: 'heading-0',
    },
    {
      id: 'toc-1',
      title: 'Internal TOC Details',
      level: 2,
      page: 1,
      page_start: 1,
      page_end: 1,
      anchor_id: 'heading-1',
    },
  ],
  attachments: [],
};

describe('CustomerDocumentPage', () => {
  const originalGetSelection = window.getSelection;

  beforeEach(() => {
    mockGetDocument.mockResolvedValue(documentPayload);
    mockGetRelatedDocuments.mockResolvedValue([]);
    mockSubmitFeedback.mockResolvedValue({
      id: 101,
      document_id: 7,
      document_title: 'Customer Guide',
      ticket_id: null,
      feedback_type: 'suggestion',
      content: 'u sure?',
      anchor_text: 'Important selected sentence for feedback.',
      status: 'pending',
      created_at: '2026-03-28T12:05:00Z',
      updated_at: '2026-03-28T12:05:00Z',
    });
    mockUpdateReadingProgress.mockResolvedValue({});
    HTMLElement.prototype.scrollIntoView = vi.fn();
    window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
  });

  afterEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, 'getSelection', {
      configurable: true,
      value: originalGetSelection,
    });
  });

  it('renders a TOC from the published document content', async () => {
    renderPage();

    await screen.findByText('Customer Guide');

    expect(screen.getAllByText('Internal TOC Intro').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Internal TOC Details').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Contents').length).toBeGreaterThan(0);
  });

  it('navigates TOC items to the matching rendered section and supports dark theme', async () => {
    renderPage();

    await screen.findByText('Customer Guide');

    fireEvent.click(screen.getAllByRole('button', { name: /use dark theme/i })[0]!);
    expect(screen.getByTestId('customer-document-paper')).toHaveClass(
      'document-preview-paper--dark'
    );

    fireEvent.click(screen.getAllByText('Internal TOC Details')[0]!);

    await waitFor(() => {
      expect(window.scrollTo).toHaveBeenCalled();
    });
  });

  it('submits short feedback from a selected excerpt', async () => {
    const selectionMock = {
      isCollapsed: false,
      toString: () => 'Important selected sentence for feedback.',
      getRangeAt: () => ({
        getBoundingClientRect: () => ({
          left: 100,
          width: 120,
          top: 140,
        }),
      }),
      removeAllRanges: vi.fn(),
    };
    Object.defineProperty(window, 'getSelection', {
      configurable: true,
      value: vi.fn(() => selectionMock as unknown as Selection),
    });

    renderPage();

    await screen.findByText('Customer Guide');
    const contentContainer = screen
      .getByText('Welcome to the document.')
      .closest('#document-content-area');
    expect(contentContainer).toBeTruthy();

    fireEvent.pointerUp(contentContainer!);
    fireEvent.click(await screen.findByRole('button', { name: /add feedback/i }));

    const popupTitle = await screen.findByText(/feedback on selection/i);
    const popup = popupTitle.closest('.inline-comment-popup');
    expect(popup).toBeTruthy();

    fireEvent.change(
      within(popup as HTMLElement).getByPlaceholderText(
        /describe what should change or what needs clarification/i
      ),
      { target: { value: 'u sure?' } }
    );

    fireEvent.click(within(popup as HTMLElement).getByRole('button', { name: /send feedback/i }));

    await waitFor(() => {
      expect(mockSubmitFeedback).toHaveBeenCalledWith({
        document_id: 7,
        feedback_type: 'suggestion',
        content: 'u sure?',
        anchor_text: 'Important selected sentence for feedback.',
      });
    });
  });
});
