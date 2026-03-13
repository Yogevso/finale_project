export async function writeText(text: string): Promise<void> {
  if (!navigator.clipboard?.writeText) {
    throw new Error('Clipboard API unavailable')
  }

  await navigator.clipboard.writeText(text)
}
