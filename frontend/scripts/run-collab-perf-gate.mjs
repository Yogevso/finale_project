#!/usr/bin/env node

import fs from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { performance } from 'node:perf_hooks'

import { HocuspocusProvider } from '@hocuspocus/provider'
import * as Y from 'yjs'

const DEFAULT_CONFIG = {
  backendUrl: 'http://127.0.0.1:8000',
  collabUrl: 'ws://127.0.0.1:8002',
  username: 'admin',
  password: 'admin123',
  users: 3,
  rounds: 3,
  timeoutMs: 15000,
  reportFile: null,
  documentId: null,
  verbose: false,
}

const BUDGETS = {
  syncP95Ms: 2500,
  propagationP95Ms: 2000,
  minSyncSuccessRatio: 1.0,
}

function parseArgs(argv) {
  const config = { ...DEFAULT_CONFIG }
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]
    const next = argv[index + 1]
    switch (arg) {
      case '--backend-url':
        config.backendUrl = next
        index += 1
        break
      case '--collab-url':
        config.collabUrl = next
        index += 1
        break
      case '--username':
        config.username = next
        index += 1
        break
      case '--password':
        config.password = next
        index += 1
        break
      case '--users':
        config.users = Number.parseInt(next, 10)
        index += 1
        break
      case '--rounds':
        config.rounds = Number.parseInt(next, 10)
        index += 1
        break
      case '--timeout-ms':
        config.timeoutMs = Number.parseInt(next, 10)
        index += 1
        break
      case '--report-file':
        config.reportFile = next
        index += 1
        break
      case '--document-id':
        config.documentId = Number.parseInt(next, 10)
        index += 1
        break
      case '--verbose':
        config.verbose = true
        break
      default:
        throw new Error(`Unknown argument: ${arg}`)
    }
  }
  return config
}

function percentile(samples, ratio) {
  if (!samples.length) {
    return 0
  }
  const ordered = [...samples].sort((left, right) => left - right)
  const index = Math.max(0, Math.min(ordered.length - 1, Math.ceil(ordered.length * ratio) - 1))
  return ordered[index]
}

function p50(samples) {
  if (!samples.length) {
    return 0
  }
  const ordered = [...samples].sort((left, right) => left - right)
  const midpoint = Math.floor(ordered.length / 2)
  if (ordered.length % 2 === 0) {
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2
  }
  return ordered[midpoint]
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options)
  const text = await response.text()
  let body = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }
  if (!response.ok) {
    throw new Error(`Request failed ${response.status} ${url}: ${typeof body === 'string' ? body : JSON.stringify(body)}`)
  }
  return body
}

async function login(backendUrl, username, password) {
  const body = await requestJson(`${backendUrl}/api/v1/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  })
  return body.access_token
}

async function resolveDocumentId(backendUrl, accessToken, explicitDocumentId) {
  if (explicitDocumentId) {
    return explicitDocumentId
  }

  const body = await requestJson(`${backendUrl}/api/v1/documents?page=1&per_page=1`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })
  const firstItem = body?.items?.[0]
  if (!firstItem?.id) {
    throw new Error('No document available for the collaboration perf gate.')
  }
  return Number(firstItem.id)
}

async function getCollabToken(backendUrl, accessToken, documentId) {
  return requestJson(`${backendUrl}/api/v1/auth/collab-token`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ document_id: documentId }),
  })
}

function resolveCollabBaseUrl(configuredUrl, issuedWebsocketUrl) {
  if (configuredUrl) {
    return configuredUrl
  }
  const websocketUrl = issuedWebsocketUrl
  if (!websocketUrl) {
    throw new Error('No collaboration websocket URL is available for the perf gate.')
  }
  const marker = '/document/'
  const index = websocketUrl.lastIndexOf(marker)
  if (index === -1) {
    return websocketUrl
  }
  return websocketUrl.slice(0, index)
}

async function connectProvider({ url, documentId, token, userLabel, timeoutMs, verbose }) {
  const doc = new Y.Doc()
  const connectionStartedAt = performance.now()
  let resolved = false
  let timeoutId = null
  let lastStatus = 'initial'
  let lastCloseEvent = null
  const webSocketPolyfill = await resolveWebSocketPolyfill()

  return new Promise((resolve, reject) => {
    const provider = new HocuspocusProvider({
      url,
      WebSocketPolyfill: webSocketPolyfill,
      name: `document/${documentId}`,
      document: doc,
      token,
      onOpen: () => {
        if (verbose) {
          console.log(`[collab-perf] ${userLabel} websocket opened`)
        }
      },
      onConnect: () => {
        if (verbose) {
          console.log(`[collab-perf] ${userLabel} provider connected`)
        }
      },
      onStatus: ({ status }) => {
        lastStatus = status
        if (verbose) {
          console.log(`[collab-perf] ${userLabel} status=${status}`)
        }
      },
      onAuthenticated: ({ scope }) => {
        if (verbose) {
          console.log(`[collab-perf] ${userLabel} authenticated scope=${scope ?? 'unknown'}`)
        }
      },
      onSynced: () => {
        if (resolved) {
          return
        }
        resolved = true
        if (timeoutId) {
          clearTimeout(timeoutId)
        }
        const syncLatencyMs = performance.now() - connectionStartedAt
        if (verbose) {
          console.log(`[collab-perf] ${userLabel} synced in ${syncLatencyMs.toFixed(1)}ms`)
        }
        resolve({
          doc,
          provider,
          syncLatencyMs,
          text: doc.getText('content'),
        })
      },
      onAuthenticationFailed: ({ reason }) => {
        if (resolved) {
          return
        }
        resolved = true
        if (timeoutId) {
          clearTimeout(timeoutId)
        }
        reject(new Error(`${userLabel} authentication failed: ${reason}`))
      },
      onClose: ({ event }) => {
        lastCloseEvent = event
        if (verbose) {
          console.log(
            `[collab-perf] ${userLabel} close code=${event?.code ?? 'unknown'} reason=${event?.reason ?? ''}`,
          )
        }
      },
      onDisconnect: () => {
        if (resolved) {
          return
        }
        resolved = true
        if (timeoutId) {
          clearTimeout(timeoutId)
        }
        const code = lastCloseEvent?.code ?? 'unknown'
        const reason = lastCloseEvent?.reason ? ` reason=${lastCloseEvent.reason}` : ''
        reject(new Error(`${userLabel} disconnected before sync completed (status=${lastStatus}, close_code=${code}${reason})`))
      },
    })

    provider.setAwarenessField('user', {
      userId: userLabel,
      username: userLabel,
      color: '#2563eb',
    })

    timeoutId = setTimeout(() => {
      if (resolved) {
        return
      }
      resolved = true
      provider.destroy()
      doc.destroy()
      reject(new Error(`${userLabel} did not sync within ${timeoutMs}ms`))
    }, timeoutMs)
  })
}

async function resolveWebSocketPolyfill() {
  try {
    const wsModule = await import('ws')
    return wsModule.WebSocket ?? wsModule.default
  } catch {
    if (typeof WebSocket !== 'undefined') {
      return WebSocket
    }
    throw new Error('No WebSocket implementation available for the collaboration perf gate.')
  }
}

async function waitForMarker(doc, marker, timeoutMs) {
  const text = doc.getText('content')
  if (text.toString().includes(marker)) {
    return
  }

  return new Promise((resolve, reject) => {
    let timeoutId = null

    const cleanup = () => {
      doc.off('update', onUpdate)
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }

    const onUpdate = () => {
      if (!text.toString().includes(marker)) {
        return
      }
      cleanup()
      resolve()
    }

    timeoutId = setTimeout(() => {
      cleanup()
      reject(new Error(`Marker ${marker} did not reach follower in ${timeoutMs}ms`))
    }, timeoutMs)

    doc.on('update', onUpdate)
  })
}

async function writeReport(reportFile, payload) {
  if (!reportFile) {
    return
  }
  const absolutePath = path.resolve(reportFile)
  await fs.mkdir(path.dirname(absolutePath), { recursive: true })
  await fs.writeFile(absolutePath, JSON.stringify(payload, null, 2), 'utf8')
}

async function main() {
  const config = parseArgs(process.argv.slice(2))
  const accessToken = await login(config.backendUrl, config.username, config.password)
  const documentId = await resolveDocumentId(config.backendUrl, accessToken, config.documentId)

  const connectedClients = []
  const syncLatencies = []

  try {
    for (let index = 0; index < config.users; index += 1) {
      const collabAuth = await getCollabToken(config.backendUrl, accessToken, documentId)
      const url = resolveCollabBaseUrl(config.collabUrl, collabAuth.websocket_url)
      const connected = await connectProvider({
        url,
        documentId,
        token: collabAuth.token,
        userLabel: `perf-user-${index + 1}`,
        timeoutMs: config.timeoutMs,
        verbose: config.verbose,
      })
      connectedClients.push(connected)
      syncLatencies.push(connected.syncLatencyMs)
    }

    await new Promise((resolve) => setTimeout(resolve, 250))

    const leader = connectedClients[0]
    const followers = connectedClients.slice(1)
    const propagationLatencies = []

    for (let round = 0; round < config.rounds; round += 1) {
      const marker = `[perf-round-${round}-${Date.now()}]`
      const waits = followers.map((client) => waitForMarker(client.doc, marker, config.timeoutMs))
      const startedAt = performance.now()
      leader.text.insert(leader.text.length, marker)
      await Promise.all(waits)
      propagationLatencies.push(performance.now() - startedAt)
    }

    const syncSuccessRatio = connectedClients.length / config.users
    const report = {
      passed: true,
      config: {
        backendUrl: config.backendUrl,
        collabUrl: config.collabUrl,
        users: config.users,
        rounds: config.rounds,
        documentId,
      },
      budgets: BUDGETS,
      metrics: {
        sync: {
          p50_ms: p50(syncLatencies),
          p95_ms: percentile(syncLatencies, 0.95),
          samples_ms: syncLatencies,
          success_ratio: syncSuccessRatio,
        },
        propagation: {
          p50_ms: p50(propagationLatencies),
          p95_ms: percentile(propagationLatencies, 0.95),
          samples_ms: propagationLatencies,
        },
      },
      failures: [],
    }

    if (report.metrics.sync.success_ratio < BUDGETS.minSyncSuccessRatio) {
      report.passed = false
      report.failures.push(
        `sync success ratio ${report.metrics.sync.success_ratio.toFixed(2)} below ${BUDGETS.minSyncSuccessRatio.toFixed(2)}`,
      )
    }
    if (report.metrics.sync.p95_ms > BUDGETS.syncP95Ms) {
      report.passed = false
      report.failures.push(
        `sync p95 ${report.metrics.sync.p95_ms.toFixed(1)}ms exceeded budget ${BUDGETS.syncP95Ms}ms`,
      )
    }
    if (report.metrics.propagation.p95_ms > BUDGETS.propagationP95Ms) {
      report.passed = false
      report.failures.push(
        `propagation p95 ${report.metrics.propagation.p95_ms.toFixed(1)}ms exceeded budget ${BUDGETS.propagationP95Ms}ms`,
      )
    }

    await writeReport(config.reportFile, report)

    console.log('Collaboration performance gate summary:')
    console.log(JSON.stringify(report, null, 2))

    if (!report.passed) {
      process.exitCode = 1
    }
  } finally {
    for (const client of connectedClients) {
      client.provider.destroy()
      client.doc.destroy()
    }
  }
}

main().catch(async (error) => {
  const report = {
    passed: false,
    failures: [error instanceof Error ? error.message : String(error)],
  }
  const argIndex = process.argv.indexOf('--report-file')
  if (argIndex !== -1 && process.argv[argIndex + 1]) {
    await writeReport(process.argv[argIndex + 1], report)
  }
  console.error(error)
  process.exit(1)
})
