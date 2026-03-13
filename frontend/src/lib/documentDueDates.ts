const parseDateOnly = (value: string | null | undefined): Date | null => {
  if (!value) {
    return null
  }

  const parts = value.split('-').map((part) => Number(part))
  if (parts.length !== 3 || parts.some((part) => !Number.isInteger(part))) {
    return null
  }

  const [year, month, day] = parts
  const parsed = new Date(year, month - 1, day)
  if (
    parsed.getFullYear() !== year ||
    parsed.getMonth() !== month - 1 ||
    parsed.getDate() !== day
  ) {
    return null
  }
  return parsed
}

export const formatDueDate = (value: string | null | undefined): string => {
  const parsed = parseDateOnly(value)
  if (!parsed) {
    return 'No due date'
  }
  return parsed.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export const isOverdueDueDate = (value: string | null | undefined): boolean => {
  const parsed = parseDateOnly(value)
  if (!parsed) {
    return false
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return parsed.getTime() < today.getTime()
}
