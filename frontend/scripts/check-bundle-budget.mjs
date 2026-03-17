#!/usr/bin/env node

/**
 * AA-013 / AA-024: Performance Budget Enforcement
 *
 * Checks that the frontend production build meets performance budgets:
 *   - Total JS bundle size < 500 KB (gzipped)
 *   - Total CSS bundle size < 100 KB (gzipped)
 *
 * Usage:
 *   cd frontend && npm run build && node scripts/check-bundle-budget.mjs
 *
 * Exit code 0 = pass, 1 = budget exceeded.
 */

import { readdirSync, statSync } from 'fs';
import { join, extname } from 'path';
import { gzipSync } from 'zlib';
import { readFileSync } from 'fs';

const DIST_DIR = join(import.meta.dirname, '..', 'dist');
const ASSETS_DIR = join(DIST_DIR, 'assets');

const BUDGETS = {
  js: { maxKB: 500, label: 'JavaScript' },
  css: { maxKB: 100, label: 'CSS' },
};

function getFilesRecursively(dir) {
  const results = [];
  try {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const fullPath = join(dir, entry.name);
      if (entry.isDirectory()) {
        results.push(...getFilesRecursively(fullPath));
      } else {
        results.push(fullPath);
      }
    }
  } catch {
    // Directory may not exist
  }
  return results;
}

function checkBudgets() {
  const files = getFilesRecursively(ASSETS_DIR);
  const totals = { js: 0, css: 0 };
  const details = { js: [], css: [] };

  for (const filePath of files) {
    const ext = extname(filePath).slice(1).toLowerCase();
    if (ext !== 'js' && ext !== 'css') continue;

    const raw = readFileSync(filePath);
    const gzipped = gzipSync(raw);
    const sizeKB = gzipped.length / 1024;

    totals[ext] += sizeKB;
    details[ext].push({
      file: filePath.replace(DIST_DIR + '/', '').replace(DIST_DIR + '\\', ''),
      rawKB: (raw.length / 1024).toFixed(1),
      gzipKB: sizeKB.toFixed(1),
    });
  }

  console.log('\n📊 Performance Budget Report');
  console.log('═'.repeat(60));

  let failed = false;

  for (const [ext, budget] of Object.entries(BUDGETS)) {
    const totalKB = totals[ext];
    const pass = totalKB <= budget.maxKB;
    const status = pass ? '✅ PASS' : '❌ FAIL';

    console.log(`\n${budget.label}: ${totalKB.toFixed(1)} KB gzipped (budget: ${budget.maxKB} KB) ${status}`);

    for (const d of details[ext]) {
      console.log(`  ${d.file}: ${d.rawKB} KB raw, ${d.gzipKB} KB gzipped`);
    }

    if (!pass) failed = true;
  }

  console.log('\n' + '═'.repeat(60));

  if (failed) {
    console.error('\n❌ Performance budget exceeded! See details above.');
    process.exit(1);
  } else {
    console.log('\n✅ All performance budgets met.');
  }
}

checkBudgets();
