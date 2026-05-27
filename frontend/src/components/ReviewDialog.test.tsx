import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ReviewDialog from './ReviewDialog';
import type { ReviewRequest } from '@/types';

vi.mock('@/lib/api', () => ({
  api: {
    getAttachmentReaderView: vi.fn(),
    getAttachments: vi.fn(),
    getComments: vi.fn(),
    getPreApprovePolicy: vi.fn(),
    getVersion: vi.fn(),
    getVersions: vi.fn(),
    updateComment: vi.fn(),
  },
}));

import { api } from '@/lib/api';

const previousVersion = {
  id: 10,
  document_id: 42,
  version_number: 1,
  semantic_version: '1.0.0',
  content: '<h1>Overview</h1><p>Before review</p><h2>Legacy Section</h2><p>Legacy copy</p>',
  changes_summary: 'Original baseline',
  is_published: false,
  created_by: 5,
  created_at: '2025-12-30T12:00:00Z',
} as const;

const currentVersion = {
  id: 11,
  document_id: 42,
  version_number: 2,
  semantic_version: '1.1.0',
  content: '<h1>Overview</h1><p>After review</p><h2>New Section</h2><p>Updated copy</p>',
  changes_summary: 'Updated introduction and added a new section',
  is_published: false,
  created_by: 7,
  created_at: '2026-01-01T12:00:00Z',
  created_by_user: {
    id: 7,
    full_name: 'Taylor Reviewer',
    role: 'manager',
  },
} as const;

const intermediateVersion = {
  id: 12,
  document_id: 42,
  version_number: 1,
  semantic_version: '1.0.1',
  content: '<h1>Overview</h1><p>Interim changes</p><h2>Legacy Section</h2><p>Interim legacy copy</p>',
  changes_summary: 'Interim changes',
  is_published: false,
  created_by: 6,
  created_at: '2025-12-31T12:00:00Z',
} as const;

function buildReview(overrides: Partial<ReviewRequest> = {}): ReviewRequest {
  return {
    id: 1,
    document_id: 42,
    version_id: 11,
    submitted_by: 7,
    reviewed_by: null,
    status: 'pending',
    message: 'Please take a look at the latest draft.',
    review_comments: null,
    submitted_at: '2026-01-01T12:00:00Z',
    reviewed_at: null,
    created_at: '2026-01-01T12:00:00Z',
    document: {
      id: 42,
      title: 'Security Policy',
      document_number: 'DOC-42',
    } as ReviewRequest['document'],
    submitter: {
      id: 7,
      full_name: 'Taylor Reviewer',
    } as ReviewRequest['submitter'],
    ...overrides,
  };
}

function renderDialog(review: ReviewRequest) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ReviewDialog
          review={review}
          onClose={vi.fn()}
          onApprove={vi.fn()}
          onReject={vi.fn()}
          isLoading={false}
        />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

describe('ReviewDialog', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(api.getPreApprovePolicy).mockResolvedValue({
      can_approve: true,
      audience_summary: 'Document is internal only',
      checks: [
        {
          id: 'review_pending',
          label: 'Review is pending',
          passed: true,
          message: null,
        },
      ],
      warnings: [],
    });
    vi.mocked(api.getVersion).mockImplementation(async (_documentId, versionId) => {
      if (versionId === 11) {
        return currentVersion as never;
      }

      return previousVersion as never;
    });
    vi.mocked(api.getVersions).mockResolvedValue({
      items: [currentVersion, previousVersion],
      total: 2,
    } as never);
    vi.mocked(api.getAttachments).mockResolvedValue([
      {
        id: 501,
        document_id: 42,
        filename: 'security-policy.docx',
        original_filename: 'security-policy.docx',
        file_size: 1024,
        mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        reader_html_status: 'ready',
        reader_toc_source: 'headings',
        uploaded_by: 7,
        uploaded_at: '2026-01-01T11:00:00Z',
      },
    ] as never);
    vi.mocked(api.getAttachmentReaderView).mockResolvedValue({
      attachment_id: 501,
      status: 'ready',
      html_content: currentVersion.content,
      toc_items: [
        { id: 'toc-overview', title: 'Overview', level: 1, page: 1, page_start: 1 },
        { id: 'toc-new', title: 'New Section', level: 2, page: 2, page_start: 2 },
      ],
      toc_source: 'headings',
      warnings: [],
      confidence: 0.98,
      error: null,
      generated_at: '2026-01-01T11:30:00Z',
    } as never);
    vi.mocked(api.getComments).mockResolvedValue([] as never);
    vi.mocked(api.updateComment).mockResolvedValue({ id: 1 } as never);
  });

  it('shows inline rejection guidance instead of using a browser alert', async () => {
    const user = userEvent.setup();

    renderDialog(buildReview());

    expect(screen.getByRole('dialog', { name: /review document/i })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /start review/i })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /start review/i }));
    await user.click(screen.getByRole('button', { name: /next section/i }));
    await user.click(screen.getByRole('button', { name: /next section/i }));
    await user.click(screen.getByRole('button', { name: /go to final review/i }));
    expect(await screen.findByText(/approval policy/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /suggest changes/i }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Add a general note or at least one section suggestion before sending the review back.'
    );
    expect(screen.getByRole('textbox', { name: /general review note/i })).toHaveAttribute(
      'aria-invalid',
      'true'
    );
  });

  it('starts a guided section review using the changed toc sections', async () => {
    const user = userEvent.setup();

    renderDialog(buildReview());

    expect(await screen.findByRole('button', { name: /start review/i })).toBeInTheDocument();
    expect(screen.getByText(/read each changed section in the document flow/i)).toBeInTheDocument();
    expect((await screen.findAllByText('Overview')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('New Section')).length).toBeGreaterThan(0);

    await user.click(screen.getByRole('button', { name: /start review/i }));

    expect(screen.getByText(/reviewing section 1 of 3/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /next section/i })).toBeInTheDocument();
  });

  it('uses the earliest contentful version as baseline when no reviewed or published baseline exists', async () => {
    vi.mocked(api.getVersions).mockResolvedValueOnce({
      items: [currentVersion, intermediateVersion, previousVersion],
      total: 3,
    } as never);
    vi.mocked(api.getVersion).mockImplementationOnce(async (_documentId, versionId) => {
      if (versionId === 11) {
        return currentVersion as never;
      }
      if (versionId === 12) {
        return intermediateVersion as never;
      }
      return previousVersion as never;
    });

    renderDialog(buildReview());

    expect(await screen.findByText(/against/i)).toHaveTextContent('against v1.0.0');
  });

  it('disables approval when the preflight policy blocks approval', async () => {
    const user = userEvent.setup();

    vi.mocked(api.getPreApprovePolicy).mockResolvedValueOnce({
      can_approve: false,
      audience_summary: 'Document is internal only',
      checks: [
        {
          id: 'user_can_approve',
          label: 'User can approve this review',
          passed: false,
          message: 'User role cannot approve this submission',
        },
      ],
      warnings: [],
    });

    renderDialog(buildReview());

    await user.click(await screen.findByRole('button', { name: /start review/i }));
    await user.click(screen.getByRole('button', { name: /next section/i }));
    await user.click(screen.getByRole('button', { name: /next section/i }));
    await user.click(screen.getByRole('button', { name: /go to final review/i }));

    expect(await screen.findByText('User role cannot approve this submission')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /approve/i })).toBeDisabled();
  });

  it('shows shared submitter comments alongside current review threads', async () => {
    const user = userEvent.setup();

    vi.mocked(api.getComments).mockImplementation(async (_documentId, _parentId, reviewId) => {
      if (reviewId === 1) {
        return [
          {
            id: 401,
            document_id: 42,
            user_id: 9,
            author_name: 'Assigned Reviewer',
            review_id: 1,
            parent_id: null,
            content: 'Reviewer thread note',
            is_private: false,
            anchor_text: 'Overview',
            anchor_id: 'overview',
            is_resolved: false,
            created_at: '2026-01-01T12:05:00Z',
            updated_at: '2026-01-01T12:05:00Z',
            replies: [],
            reply_count: 0,
          },
        ] as never;
      }

      return [
        {
          id: 401,
          document_id: 42,
          user_id: 9,
          author_name: 'Assigned Reviewer',
          review_id: 1,
          parent_id: null,
          content: 'Reviewer thread note',
          is_private: false,
          anchor_text: 'Overview',
          anchor_id: 'overview',
          is_resolved: false,
          created_at: '2026-01-01T12:05:00Z',
          updated_at: '2026-01-01T12:05:00Z',
          replies: [],
          reply_count: 0,
        },
        {
          id: 402,
          document_id: 42,
          user_id: 7,
          author_name: 'Submitter',
          review_id: null,
          parent_id: null,
          content: 'Please validate this source table.',
          is_private: false,
          anchor_text: 'Project Type',
          anchor_id: 'project-type',
          is_resolved: false,
          created_at: '2026-01-01T12:04:00Z',
          updated_at: '2026-01-01T12:04:00Z',
          replies: [],
          reply_count: 0,
        },
        {
          id: 403,
          document_id: 42,
          user_id: 8,
          author_name: 'Previous Reviewer',
          review_id: 999,
          parent_id: null,
          content: 'Historical review thread.',
          is_private: false,
          anchor_text: 'Legacy Section',
          anchor_id: 'legacy',
          is_resolved: false,
          created_at: '2026-01-01T12:03:00Z',
          updated_at: '2026-01-01T12:03:00Z',
          replies: [],
          reply_count: 0,
        },
      ] as never;
    });
  it('persists the reviewed version id when opening the document from review', async () => {
    const user = userEvent.setup();
    const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

    renderDialog(buildReview());

    await user.click(await screen.findByRole('button', { name: /start review/i }));
    await user.click(screen.getByRole('button', { name: /next section/i }));
    await user.click(screen.getByRole('button', { name: /next section/i }));
    await user.click(screen.getByRole('button', { name: /go to final review/i }));

    expect(await screen.findByText('Reviewer thread note')).toBeInTheDocument();
    expect(screen.getByText('Please validate this source table.')).toBeInTheDocument();
    expect(screen.queryByText('Historical review thread.')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /open.*new tab/i }));

    const rawSessionStore = window.localStorage.getItem('reviews.document.session.v1');
    expect(rawSessionStore).not.toBeNull();

    const parsedSessionStore = JSON.parse(rawSessionStore || '{}');
    expect(parsedSessionStore['1']).toMatchObject({
      reviewId: 1,
      documentId: 42,
      versionId: 11,
      mode: 'review',
    });
    expect(windowOpenSpy).toHaveBeenCalled();

    windowOpenSpy.mockRestore();
  });
});
