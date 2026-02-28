#!/usr/bin/env node
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '..', '..')

const defaultOpenApiUrl = 'http://localhost:8000/api/v1/openapi.json'
const sourceUrl = process.argv[2] || process.env.OPENAPI_URL || defaultOpenApiUrl
const outputPath = path.join(repoRoot, 'backend', 'openapi.contract.json')

function sortJson(value) {
  if (Array.isArray(value)) {
    return value.map(sortJson)
  }
  if (value && typeof value === 'object') {
    return Object.keys(value)
      .sort()
      .reduce((acc, key) => {
        acc[key] = sortJson(value[key])
        return acc
      }, {})
  }
  return value
}

async function main() {
  const response = await fetch(sourceUrl)
  if (!response.ok) {
    throw new Error(`Failed to fetch OpenAPI schema from ${sourceUrl}: ${response.status}`)
  }

  const sourceJson = await response.json()
  const normalized = sortJson(sourceJson)
  const rendered = `${JSON.stringify(normalized, null, 2)}\n`

  await fs.writeFile(outputPath, rendered, 'utf8')
  console.log(`Wrote OpenAPI snapshot: ${outputPath}`)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})

