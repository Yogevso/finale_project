#!/usr/bin/env node
/**
 * AH-015: Security audit gate for npm packages.
 *
 * Runs `npm audit` and exits non-zero if high/critical vulnerabilities are found.
 * Designed to be run in CI/CD pipelines.
 *
 * Usage:
 *   node scripts/npm_audit_gate.js [--prod]
 */

const { execSync } = require('child_process');
const path = require('path');

const isProd = process.argv.includes('--prod');
const auditLevel = isProd ? 'high' : 'moderate';

const dirs = ['frontend', 'collab-server'];

let failed = false;

for (const dir of dirs) {
  const fullPath = path.join(__dirname, '..', dir);
  console.log(`\n[npm-audit] Auditing ${dir}...`);

  try {
    execSync(`npm audit --audit-level=${auditLevel}`, {
      cwd: fullPath,
      stdio: 'inherit',
    });
    console.log(`[PASS] ${dir}`);
  } catch (error) {
    console.error(`[FAIL] ${dir} has vulnerabilities at ${auditLevel} level or higher`);
    failed = true;
  }
}

if (failed) {
  console.error('\n[FAIL] npm audit found vulnerabilities. Fix before deploying.');
  process.exit(1);
}

console.log('\n[PASS] All npm audits passed.');
process.exit(0);
