import { spawn, spawnSync } from 'node:child_process'
import { mkdirSync, rmSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptFile = fileURLToPath(import.meta.url)
const scriptDir = path.dirname(scriptFile)
const backendDir = path.resolve(scriptDir, '../../backend')
const backendTempDir = path.resolve(backendDir, 'temp')
const defaultDbPath = path.resolve(backendTempDir, `playwright-e2e-${Date.now()}.db`)
const defaultDatabaseUrl = `sqlite:///${defaultDbPath.replace(/\\/g, '/')}`
const databaseUrl = process.env.DATABASE_URL?.trim() || defaultDatabaseUrl

mkdirSync(backendTempDir, { recursive: true })
rmSync(path.resolve(backendTempDir, 'playwright-e2e.db'), { force: true })

const backendEnv = {
  ...process.env,
  APP_ENV: process.env.APP_ENV ?? 'testing',
  SECRET_KEY: process.env.SECRET_KEY ?? 'test-secret-key',
  DATABASE_URL: databaseUrl,
  PYTHONUTF8: process.env.PYTHONUTF8 ?? '1',
}

const pythonCandidates = [process.env.PYTHON, 'python', 'py'].filter(Boolean)
const pythonCommand = pythonCandidates.find((candidate) => {
  const probe = spawnSync(candidate, ['--version'], {
    cwd: backendDir,
    env: backendEnv,
    stdio: 'ignore',
  })
  return probe.status === 0
})

if (!pythonCommand) {
  console.error('Unable to find a Python executable for E2E backend startup.')
  process.exit(1)
}

function runOrThrow(args) {
  const result = spawnSync(pythonCommand, args, {
    cwd: backendDir,
    env: backendEnv,
    stdio: 'inherit',
  })
  if (result.error) {
    console.error(`Command failed to start: ${pythonCommand} ${args.join(' ')}`)
    console.error(result.error)
    process.exit(1)
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }
}

console.log(`Using Python command: ${pythonCommand}`)
console.log(`Using E2E database: ${backendEnv.DATABASE_URL}`)
runOrThrow(['-m', 'alembic', 'upgrade', 'heads'])
runOrThrow(['seed_data.py'])

const server = spawn(
  pythonCommand,
  ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8010'],
  {
    cwd: backendDir,
    env: backendEnv,
    stdio: 'inherit',
  },
)

const forwardSignal = (signal) => {
  if (!server.killed) {
    server.kill(signal)
  }
}

process.on('SIGINT', () => forwardSignal('SIGINT'))
process.on('SIGTERM', () => forwardSignal('SIGTERM'))

server.on('exit', (code) => {
  process.exit(code ?? 0)
})
