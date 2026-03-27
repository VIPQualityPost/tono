import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, '..');
const args = new Set(process.argv.slice(2));
const mode = args.has('--mode=native') || args.has('--native') ? 'native' : 'frontend';

const removed = [];

function removePath(targetPath) {
  if (!fs.existsSync(targetPath)) return;
  fs.rmSync(targetPath, { recursive: true, force: true });
  removed.push(path.relative(repoRoot, targetPath) || '.');
}

function removePythonCaches(rootPath) {
  const stack = [rootPath];
  const skipDirs = new Set(['.git', '.venv', 'node_modules']);

  while (stack.length > 0) {
    const current = stack.pop();
    let entries = [];

    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      continue;
    }

    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);

      if (entry.isDirectory()) {
        if (entry.name === '__pycache__') {
          removePath(fullPath);
          continue;
        }
        if (skipDirs.has(entry.name)) continue;
        stack.push(fullPath);
        continue;
      }

      if (entry.isFile() && (entry.name.endsWith('.pyc') || entry.name.endsWith('.pyo'))) {
        try {
          fs.rmSync(fullPath, { force: true });
          removed.push(path.relative(repoRoot, fullPath) || '.');
        } catch {
          // Ignore files held open by another process; the rest of the clean can still continue.
        }
      }
    }
  }
}

removePath(path.join(repoRoot, 'frontend', 'dist'));
removePath(path.join(repoRoot, 'frontend', 'node_modules', '.vite'));
removePythonCaches(repoRoot);

if (mode === 'native') {
  removePath(path.join(repoRoot, 'desktop-build'));
  removePath(path.join(repoRoot, 'desktop-dist'));
}

if (removed.length === 0) {
  console.log(`[clean] No cached build artifacts found (${mode}).`);
} else {
  console.log(`[clean] Removed ${removed.length} artifact${removed.length === 1 ? '' : 's'} (${mode}).`);
}
