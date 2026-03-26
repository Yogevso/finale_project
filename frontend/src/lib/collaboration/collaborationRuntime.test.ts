import { describe, expect, it } from 'vitest'
import {
  getHttpStatusCode,
  parseCollabServerStatelessMessage,
  resolveCollabServerUrl,
} from './collaborationRuntime'

describe('collaborationRuntime', () => {
  it('parses persistence stateless messages', () => {
    expect(
      parseCollabServerStatelessMessage(
        JSON.stringify({
          type: 'persistence_failed',
          message: 'saving failed',
        }),
      ),
    ).toEqual({
      type: 'persistence_failed',
      message: 'saving failed',
    })

    expect(
      parseCollabServerStatelessMessage(
        JSON.stringify({
          type: 'persistence_restored',
        }),
      ),
    ).toEqual({
      type: 'persistence_restored',
    })
  })

  it('rejects invalid stateless payloads', () => {
    expect(parseCollabServerStatelessMessage('not-json')).toBeNull()
    expect(parseCollabServerStatelessMessage(JSON.stringify({ type: 'unknown' }))).toBeNull()
    expect(
      parseCollabServerStatelessMessage(
        JSON.stringify({
          type: 'persistence_failed',
        }),
      ),
    ).toBeNull()
  })

  it('extracts the collaboration server base url from websocket document urls', () => {
    expect(resolveCollabServerUrl('ws://localhost:8002/document/42')).toBe('ws://localhost:8002')
    expect(resolveCollabServerUrl('ws://localhost:8002')).toBe('ws://localhost:8002')
    expect(resolveCollabServerUrl(undefined, 'ws://fallback')).toBe('ws://fallback')
  })

  it('extracts http status codes from transport errors', () => {
    expect(getHttpStatusCode({ response: { status: 403 } })).toBe(403)
    expect(getHttpStatusCode({ response: { status: '403' } })).toBeNull()
    expect(getHttpStatusCode(null)).toBeNull()
  })
})
