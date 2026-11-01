/**
 * Build script to generate the public/ directory for Vercel static asset serving.
 * Keeps src/eventcraft/static and examples as the single source of truth.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, '..');

const publicDir = path.join(root, 'public');
const staticDir = path.join(root, 'src', 'eventcraft', 'static');
const examplesDir = path.join(root, 'examples');

if (fs.existsSync(publicDir)) {
  fs.rmSync(publicDir, { recursive: true, force: true });
}
fs.mkdirSync(publicDir, { recursive: true });

if (fs.existsSync(staticDir)) {
  fs.cpSync(staticDir, publicDir, { recursive: true });
}

if (fs.existsSync(examplesDir)) {
  fs.cpSync(examplesDir, path.join(publicDir, 'examples'), { recursive: true });
}

console.log('Successfully generated public/ directory from single source of truth.');
