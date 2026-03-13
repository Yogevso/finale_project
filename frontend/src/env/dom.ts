export function getDomParser(): DOMParser {
  return new DOMParser()
}

export function getDocument(): Document {
  return document
}

export function getWindowLocation(): Location {
  return window.location
}

export function createObjectUrl(blob: Blob): string {
  return window.URL.createObjectURL(blob)
}

export function revokeObjectUrl(objectUrl: string): void {
  window.URL.revokeObjectURL(objectUrl)
}
