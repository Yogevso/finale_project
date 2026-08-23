const DEFAULT_TIMEZONE = 'UTC'
const DEFAULT_LOCALE = 'en'

type DateFormatPreferences = {
  timezone: string
  locale: string
}

let activePreferences: DateFormatPreferences = {
  timezone: DEFAULT_TIMEZONE,
  locale: DEFAULT_LOCALE,
}

export function syncDateFormatPreferences(
  timezone: string | null | undefined,
  locale: string | null | undefined,
): void {
  activePreferences = {
    timezone: timezone?.trim() || DEFAULT_TIMEZONE,
    locale: locale?.trim() || DEFAULT_LOCALE,
  }
}

export function formatDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return iso
  }
  return date.toLocaleString(activePreferences.locale, {
    timeZone: activePreferences.timezone,
  })
}

/**
 * The one date a document is shown with, anywhere in the platform.
 *
 * There were three. `toLocaleDateString()` with no arguments follows the *browser's*
 * locale, so the same document read 8/23/2026 for one viewer and 23.8.2026 for another;
 * 19 of the 22 call sites did that. The rest pinned 'en-US' with either `month: 'short'`
 * or `month: 'long'`, and one page carried two of them at once. Locale and timezone come
 * from the user's own preferences here, not from whatever browser they opened.
 */
export function formatDocumentDate(value: string | null | undefined, fallback = '-'): string {
  if (!value) {
    return fallback
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return String(value)
  }
  return date.toLocaleDateString(activePreferences.locale, {
    timeZone: activePreferences.timezone,
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
  })
}
