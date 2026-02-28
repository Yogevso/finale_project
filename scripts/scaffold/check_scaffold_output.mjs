#!/usr/bin/env node
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'

import { generateScaffold } from './scaffold.mjs'

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

async function fileExists(filePath) {
  try {
    await fs.access(filePath)
    return true
  } catch {
    return false
  }
}

async function runCase(caseOptions) {
  const generated = await generateScaffold(caseOptions)
  assert(generated.length >= 2, `Expected at least implementation and test outputs for ${caseOptions.target}/${caseOptions.kind}`)
  return generated
}

async function verifyGeneratedFiles(baseDir, relativeFiles) {
  for (const rel of relativeFiles) {
    const abs = path.join(baseDir, rel)
    assert(await fileExists(abs), `Expected generated file missing: ${rel}`)
    const content = await fs.readFile(abs, 'utf8')
    assert(content.includes('scripts/scaffold/scaffold.mjs'), `Missing generator marker in ${rel}`)
    assert(!/\{\{[a-zA-Z0-9_]+\}\}/.test(content), `Unresolved template placeholder in ${rel}`)
  }
}

async function main() {
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'scaffold-check-'))

  try {
    const generated = []
    generated.push(
      ...(await runCase({
        outDir: tempDir,
        target: 'backend',
        kind: 'service',
        name: 'release_sync',
        context: 'authoring',
      })),
    )
    generated.push(
      ...(await runCase({
        outDir: tempDir,
        target: 'backend',
        kind: 'repository',
        name: 'release_sync',
        context: 'authoring',
      })),
    )
    generated.push(
      ...(await runCase({
        outDir: tempDir,
        target: 'backend',
        kind: 'policy',
        name: 'release_access',
        context: 'review',
      })),
    )
    generated.push(
      ...(await runCase({
        outDir: tempDir,
        target: 'backend',
        kind: 'controller',
        name: 'release_sync',
        context: 'review',
        scope: 'management',
      })),
    )
    generated.push(
      ...(await runCase({
        outDir: tempDir,
        target: 'frontend',
        kind: 'feature',
        name: 'release_dashboard',
        context: 'review',
      })),
    )
    generated.push(
      ...(await runCase({
        outDir: tempDir,
        target: 'collab',
        kind: 'port',
        name: 'document_sync',
        context: 'collaboration',
      })),
    )
    generated.push(
      ...(await runCase({
        outDir: tempDir,
        target: 'collab',
        kind: 'adapter',
        name: 'backend_document_sync',
        context: 'collaboration',
      })),
    )

    await verifyGeneratedFiles(tempDir, generated)

    const docsFiles = generated.filter((filePath) => filePath.startsWith('docs/scaffolds/'))
    assert(docsFiles.length >= 7, 'Expected docs stubs for each generated scaffold case')

    const testFiles = generated.filter(
      (filePath) =>
        filePath.includes('/tests/') ||
        filePath.includes('/__tests__/') ||
        filePath.endsWith('.test.ts'),
    )
    assert(testFiles.length >= 7, 'Expected baseline test stubs for generated scaffold cases')

    console.log('Scaffold output checks passed.')
    console.log(`Validated ${generated.length} generated files in ${tempDir}`)
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true })
  }
}

main().catch((error) => {
  console.error(error.message)
  process.exit(1)
})
