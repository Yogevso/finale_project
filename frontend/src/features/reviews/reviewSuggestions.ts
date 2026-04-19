export interface ReviewSectionSuggestion {
  title: string;
  comment: string;
}

export interface ParsedReviewSuggestions {
  generalComment: string;
  sectionSuggestions: ReviewSectionSuggestion[];
}

const GENERAL_FEEDBACK_LABEL = 'General feedback:';
const SECTION_SUGGESTIONS_LABEL = 'Section suggestions:';

export function formatReviewSuggestions(params: {
  generalComment?: string;
  sectionSuggestions: ReviewSectionSuggestion[];
}): string {
  const parts: string[] = [];
  const generalComment = params.generalComment?.trim() || '';
  const sectionSuggestions = params.sectionSuggestions.filter(
    (section) => section.title.trim().length > 0 && section.comment.trim().length > 0
  );

  if (generalComment) {
    parts.push(`${GENERAL_FEEDBACK_LABEL}\n${generalComment}`);
  }

  if (sectionSuggestions.length > 0) {
    const sectionBlock = sectionSuggestions
      .map((section) => `## ${section.title.trim()}\n${section.comment.trim()}`)
      .join('\n\n');
    parts.push(`${SECTION_SUGGESTIONS_LABEL}\n${sectionBlock}`);
  }

  return parts.join('\n\n');
}

export function parseReviewSuggestions(
  reviewComments: string | null | undefined
): ParsedReviewSuggestions {
  const text = (reviewComments || '').trim();
  if (!text) {
    return {
      generalComment: '',
      sectionSuggestions: [],
    };
  }

  const sectionIndex = text.indexOf(SECTION_SUGGESTIONS_LABEL);
  const generalIndex = text.indexOf(GENERAL_FEEDBACK_LABEL);

  let generalComment = '';
  let sectionBlock = text;

  if (generalIndex >= 0) {
    const generalStart = generalIndex + GENERAL_FEEDBACK_LABEL.length;
    const generalEnd = sectionIndex >= 0 ? sectionIndex : text.length;
    generalComment = text.slice(generalStart, generalEnd).trim();
  }

  if (sectionIndex >= 0) {
    sectionBlock = text.slice(sectionIndex + SECTION_SUGGESTIONS_LABEL.length).trim();
  } else {
    sectionBlock = '';
  }

  const sectionSuggestions = sectionBlock
    ? sectionBlock
        .split(/^## /m)
        .map((chunk) => chunk.trim())
        .filter(Boolean)
        .map((chunk) => {
          const [rawTitle, ...rest] = chunk.split('\n');
          return {
            title: (rawTitle || '').trim(),
            comment: rest.join('\n').trim(),
          };
        })
        .filter((section) => section.title.length > 0 && section.comment.length > 0)
    : [];

  if (generalIndex < 0 && sectionIndex < 0) {
    return {
      generalComment: text,
      sectionSuggestions: [],
    };
  }

  return {
    generalComment,
    sectionSuggestions,
  };
}
