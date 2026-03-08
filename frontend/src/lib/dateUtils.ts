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
