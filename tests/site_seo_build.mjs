import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = dirname(__dirname);
const siteDir = join(repoRoot, 'app', 'site');
const distDir = join(siteDir, 'dist');

const cleanupTargets = [
  'dist',
  '.astro',
  join('src', 'env.d.ts')
].map((target) => join(siteDir, target));

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    stdio: 'inherit',
    ...options
  });

  if (result.status !== 0) {
    throw new Error(`Command failed: ${command} ${args.join(' ')}`);
  }
}

function ensure(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

try {
  for (const target of cleanupTargets) {
    rmSync(target, { recursive: true, force: true });
  }

  const nodeModulesDir = join(siteDir, 'node_modules');
  if (!existsSync(nodeModulesDir)) {
    run('npm', ['install', '--no-save'], {
      cwd: siteDir,
      env: {
        ...process.env,
        npm_config_fund: 'false',
        npm_config_audit: 'false',
        npm_config_package_lock: 'false'
      }
    });
  }

  run('npm', ['run', 'build'], {
    cwd: siteDir,
    env: {
      ...process.env,
      npm_config_fund: 'false',
      npm_config_audit: 'false',
      SITE_URL: process.env.SITE_URL ?? 'https://sodmaster.example.com'
    }
  });

  ensure(existsSync(distDir), 'Astro build output directory was not created.');

  const robotsPath = join(distDir, 'robots.txt');
  ensure(existsSync(robotsPath), 'robots.txt was not emitted by the Astro build.');

  const sitemapCandidates = ['sitemap-index.xml', 'sitemap.xml'];
  const sitemapName = sitemapCandidates.find((name) => existsSync(join(distDir, name)));
  ensure(sitemapName, 'No sitemap file was emitted by the Astro build.');

  const robotsBody = readFileSync(robotsPath, 'utf-8');
  ensure(/Sitemap:\s+/.test(robotsBody), 'robots.txt does not reference a sitemap.');

  console.log(`SEO build verification succeeded (found ${robotsPath} and ${join(distDir, sitemapName)}).`);
} finally {
  for (const target of cleanupTargets) {
    rmSync(target, { recursive: true, force: true });
  }
}
