import type { SectionEditTarget, TocSection } from '@/pages/document-detail/helpers/previewHelpers'

export type ContentEditingPhase = 'idle' | 'chooser' | 'editing'

export interface ContentEditingMachineState {
  phase: ContentEditingPhase
  editingSection: SectionEditTarget | null
  handledRequestToken: number
}

export type ContentEditingMachineEvent =
  | { type: 'OPEN_CHOOSER'; token: number }
  | { type: 'MARK_REQUEST_HANDLED'; token: number }
  | { type: 'START_EDITING'; section: SectionEditTarget }
  | { type: 'BACK_TO_CHOOSER' }
  | { type: 'CLOSE_CHOOSER' }
  | { type: 'CLOSE_EDITING' }

export function createInitialContentEditingMachineState(): ContentEditingMachineState {
  return {
    phase: 'idle',
    editingSection: null,
    handledRequestToken: 0,
  }
}

export function transitionContentEditingMachineState(
  state: ContentEditingMachineState,
  event: ContentEditingMachineEvent,
): ContentEditingMachineState {
  switch (event.type) {
    case 'OPEN_CHOOSER':
      return {
        phase: 'chooser',
        editingSection: null,
        handledRequestToken: event.token,
      }
    case 'MARK_REQUEST_HANDLED':
      return {
        ...state,
        handledRequestToken: event.token,
      }
    case 'START_EDITING':
      return {
        ...state,
        phase: 'editing',
        editingSection: event.section,
      }
    case 'BACK_TO_CHOOSER':
      return {
        ...state,
        phase: 'chooser',
        editingSection: null,
      }
    case 'CLOSE_CHOOSER':
      if (state.phase !== 'chooser') {
        return state
      }
      return {
        ...state,
        phase: 'idle',
        editingSection: null,
      }
    case 'CLOSE_EDITING':
      if (state.phase !== 'editing') {
        return state
      }
      return {
        ...state,
        phase: 'idle',
        editingSection: null,
      }
    default:
      return state
  }
}

export function toSectionEditTarget(
  section: TocSection,
  options?: { fromChooser?: boolean; forceMode?: 'edit' | 'insert' | 'full' },
): SectionEditTarget {
  return {
    ...section,
    editMode: options?.forceMode ?? (section.index < 0 ? 'full' : 'edit'),
    fromChooser: options?.fromChooser ?? false,
  }
}

