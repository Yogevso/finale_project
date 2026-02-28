#!/usr/bin/env node
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '..', '..')
const templateRoot = path.join(__dirname, 'templates')

const SUPPORTED = {
  backend: new Set(['service', 'repository', 'policy', 'controller']),
  frontend: new Set(['feature']),
  collab: new Set(['port', 'adapter']),
}

function usage() {
  return [
    'Usage:',
    '  node scripts/scaffold/scaffold.mjs \\',
    '    --target <backend|frontend|collab> \\',
    '    --kind <kind> \\',
    '    --name <module-name> \\',
    '    [--context <context>] [--scope <management|portal>] [--out <path>] \\',
    '    [--force] [--dry-run] [--no-docs]',
    '',
    'Examples:',
    '  node scripts/scaffold/scaffold.mjs --target backend --kind service --name release_sync',
    '  node scripts/scaffold/scaffold.mjs --target backend --kind controller --name users --scope management',
    '  node scripts/scaffold/scaffold.mjs --target frontend --kind feature --name releaseDashboard',
    '  node scripts/scaffold/scaffold.mjs --target collab --kind adapter --name backendDocumentState',
  ].join('\n')
}

function toWords(value) {
  const normalized = value
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[^a-zA-Z0-9]+/g, ' ')
    .trim()
  if (!normalized) {
    return []
  }
  return normalized
    .split(/\s+/)
    .map((word) => word.toLowerCase())
    .filter(Boolean)
}

function toPascal(words) {
  return words.map((word) => `${word[0].toUpperCase()}${word.slice(1)}`).join('')
}

function toCamel(words) {
  if (words.length === 0) {
    return ''
  }
  const [head, ...tail] = words
  return `${head}${tail.map((word) => `${word[0].toUpperCase()}${word.slice(1)}`).join('')}`
}

function parseArgs(argv) {
  const options = {
    force: false,
    dryRun: false,
    includeDocs: true,
  }

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]
    switch (arg) {
      case '--target':
        options.target = argv[++index]
        break
      case '--kind':
        options.kind = argv[++index]
        break
      case '--name':
        options.name = argv[++index]
        break
      case '--context':
        options.context = argv[++index]
        break
      case '--scope':
        options.scope = argv[++index]
        break
      case '--out':
        options.out = argv[++index]
        break
      case '--force':
        options.force = true
        break
      case '--dry-run':
        options.dryRun = true
        break
      case '--no-docs':
        options.includeDocs = false
        break
      case '--help':
      case '-h':
        options.help = true
        break
      default:
        throw new Error(`Unknown argument: ${arg}\n\n${usage()}`)
    }
  }
  return options
}

function ensureSupported(target, kind) {
  const supportedKinds = SUPPORTED[target]
  if (!supportedKinds) {
    throw new Error(`Unsupported target "${target}". Supported: ${Object.keys(SUPPORTED).join(', ')}`)
  }
  if (!supportedKinds.has(kind)) {
    throw new Error(
      `Unsupported kind "${kind}" for target "${target}". Supported: ${Array.from(supportedKinds).join(', ')}`,
    )
  }
}

function toRelativePosix(filePath) {
  return filePath.replace(/\\/g, '/')
}

function buildNames(name) {
  const words = toWords(name)
  if (words.length === 0) {
    throw new Error(`Invalid --name "${name}"`)
  }
  return {
    words,
    snakeName: words.join('_'),
    kebabName: words.join('-'),
    pascalName: toPascal(words),
    camelName: toCamel(words),
  }
}

function docsEntry({ target, kind, names }) {
  return {
    template: 'docs/scaffold.md.tpl',
    output: path.join('docs', 'scaffolds', `${target}-${kind}-${names.kebabName}.md`),
  }
}

function filePlan({ target, kind, names, scope, includeDocs }) {
  const plan = []
  if (target === 'backend' && kind === 'service') {
    plan.push(
      {
        template: 'backend/service.py.tpl',
        output: path.join('backend', 'app', 'services', `${names.snakeName}_service.py`),
      },
      {
        template: 'backend/service.test.py.tpl',
        output: path.join('backend', 'tests', `test_${names.snakeName}_service.py`),
      },
    )
  } else if (target === 'backend' && kind === 'repository') {
    plan.push(
      {
        template: 'backend/repository.py.tpl',
        output: path.join('backend', 'app', 'repositories', `${names.snakeName}_repository.py`),
      },
      {
        template: 'backend/repository.test.py.tpl',
        output: path.join('backend', 'tests', `test_${names.snakeName}_repository.py`),
      },
    )
  } else if (target === 'backend' && kind === 'policy') {
    plan.push(
      {
        template: 'backend/policy.py.tpl',
        output: path.join('backend', 'app', 'policy', `${names.snakeName}.py`),
      },
      {
        template: 'backend/policy.test.py.tpl',
        output: path.join('backend', 'tests', `test_${names.snakeName}_policy.py`),
      },
    )
  } else if (target === 'backend' && kind === 'controller') {
    const resolvedScope = scope || 'management'
    if (!['management', 'portal'].includes(resolvedScope)) {
      throw new Error(`--scope must be "management" or "portal"; received "${resolvedScope}"`)
    }
    plan.push(
      {
        template: 'backend/controller.py.tpl',
        output: path.join(
          'backend',
          'app',
          'web',
          'controllers',
          resolvedScope,
          `${names.snakeName}_controller.py`,
        ),
      },
      {
        template: 'backend/controller.test.py.tpl',
        output: path.join('backend', 'tests', `test_${resolvedScope}_${names.snakeName}_controller.py`),
      },
    )
  } else if (target === 'frontend' && kind === 'feature') {
    const featureDir = names.camelName
    const useCasesFile = `${featureDir}UseCases`
    plan.push(
      {
        template: 'frontend/feature.index.ts.tpl',
        output: path.join('frontend', 'src', 'features', featureDir, 'index.ts'),
      },
      {
        template: 'frontend/feature.useCases.ts.tpl',
        output: path.join('frontend', 'src', 'features', featureDir, 'useCases', `${useCasesFile}.ts`),
      },
      {
        template: 'frontend/feature.useCases.test.ts.tpl',
        output: path.join(
          'frontend',
          'src',
          'features',
          featureDir,
          'useCases',
          `${useCasesFile}.test.ts`,
        ),
      },
    )
  } else if (target === 'collab' && kind === 'port') {
    plan.push(
      {
        template: 'collab/port.ts.tpl',
        output: path.join('collab-server', 'src', 'ports', `${names.camelName}Port.ts`),
      },
      {
        template: 'collab/port.test.ts.tpl',
        output: path.join('collab-server', 'src', '__tests__', `${names.camelName}Port.test.ts`),
      },
    )
  } else if (target === 'collab' && kind === 'adapter') {
    plan.push(
      {
        template: 'collab/adapter.ts.tpl',
        output: path.join('collab-server', 'src', 'adapters', `${names.camelName}Adapter.ts`),
      },
      {
        template: 'collab/adapter.test.ts.tpl',
        output: path.join('collab-server', 'src', '__tests__', `${names.camelName}Adapter.test.ts`),
      },
    )
  } else {
    throw new Error(`Unsupported target/kind combination: ${target}/${kind}`)
  }

  if (includeDocs) {
    plan.push(docsEntry({ target, kind, names }))
  }
  return plan
}

function renderTemplate(templateSource, variables) {
  return templateSource.replace(/\{\{([a-zA-Z0-9_]+)\}\}/g, (_match, key) => {
    return String(variables[key] ?? '')
  })
}

async function ensureWritable(destinationPath, force) {
  if (!force) {
    try {
      await fs.access(destinationPath)
      throw new Error(`Refusing to overwrite existing file: ${destinationPath}`)
    } catch (error) {
      if (error?.code !== 'ENOENT') {
        throw error
      }
    }
  }
}

export async function generateScaffold(rawOptions) {
  const target = rawOptions.target
  const kind = rawOptions.kind
  const name = rawOptions.name
  const context = rawOptions.context || 'general'
  const scope = rawOptions.scope
  const outDir = rawOptions.outDir ? path.resolve(rawOptions.outDir) : repoRoot
  const includeDocs = rawOptions.includeDocs !== false
  const dryRun = rawOptions.dryRun === true
  const force = rawOptions.force === true

  if (!target || !kind || !name) {
    throw new Error(`--target, --kind, and --name are required\n\n${usage()}`)
  }
  ensureSupported(target, kind)

  const names = buildNames(name)
  const resolvedScope = scope || 'management'
  const plan = filePlan({
    target,
    kind,
    names,
    scope: resolvedScope,
    includeDocs,
  })

  const variables = {
    generatedBy: 'scripts/scaffold/scaffold.mjs',
    target,
    kind,
    scope: resolvedScope,
    context,
    displayName: names.pascalName,
    snakeName: names.snakeName,
    kebabName: names.kebabName,
    camelName: names.camelName,
    pascalName: names.pascalName,
    moduleName: names.snakeName,
    className:
      kind === 'service'
        ? `${names.pascalName}Service`
        : kind === 'repository'
          ? `${names.pascalName}Repository`
          : kind === 'policy'
            ? `${names.pascalName}Policy`
            : kind === 'controller'
              ? `${names.pascalName}Controller`
              : kind === 'port'
                ? `${names.pascalName}Port`
                : kind === 'adapter'
                  ? `${names.pascalName}Adapter`
                  : names.pascalName,
    modelClass: names.pascalName,
    routePrefix: `/api/${resolvedScope}/${names.kebabName}`,
    routerTag: `${resolvedScope}-${names.kebabName}`,
    featureDir: names.camelName,
    useCasesFile: `${names.camelName}UseCases`,
    interfaceName: `${names.pascalName}UseCases`,
    docsTitle: `${target} ${kind} ${names.pascalName}`,
    testName: names.snakeName,
    timestampUtc: new Date().toISOString(),
    osLineEnd: os.EOL,
  }

  const generated = []

  for (const entry of plan) {
    const templatePath = path.join(templateRoot, entry.template)
    const outputPath = path.join(outDir, entry.output)
    const templateSource = await fs.readFile(templatePath, 'utf8')
    const rendered = renderTemplate(templateSource, variables)

    if (dryRun) {
      generated.push(toRelativePosix(entry.output))
      continue
    }

    await fs.mkdir(path.dirname(outputPath), { recursive: true })
    await ensureWritable(outputPath, force)
    await fs.writeFile(outputPath, rendered, 'utf8')
    generated.push(toRelativePosix(path.relative(outDir, outputPath)))
  }

  return generated
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
  if (args.help) {
    console.log(usage())
    return
  }

  const generated = await generateScaffold({
    target: args.target,
    kind: args.kind,
    name: args.name,
    context: args.context,
    scope: args.scope,
    outDir: args.out,
    dryRun: args.dryRun,
    force: args.force,
    includeDocs: args.includeDocs,
  })

  if (args.dryRun) {
    console.log('Planned scaffold output:')
  } else {
    console.log('Generated scaffold files:')
  }
  for (const filePath of generated) {
    console.log(`- ${filePath}`)
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  main().catch((error) => {
    console.error(error.message)
    process.exit(1)
  })
}
