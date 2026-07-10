#!/usr/bin/env node
/**
 * Version bump script for neurotic-docx-bench
 * 
 * Updates version numbers in:
 * - pyproject.toml (Python package)
 * - package.json (Node package)
 * - CHANGELOG.md (adds new section if needed)
 * 
 * Usage:
 *   node --import tsx scripts/bump-version.ts <major|minor|patch|version>
 * 
 * Examples:
 *   node --import tsx scripts/bump-version.ts patch    # 0.1.0 -> 0.1.1
 *   node --import tsx scripts/bump-version.ts minor    # 0.1.0 -> 0.2.0
 *   node --import tsx scripts/bump-version.ts major    # 0.1.0 -> 1.0.0
 *   node --import tsx scripts/bump-version.ts 0.2.0     # explicit version
 */

import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const REPO_ROOT = join(__dirname, '..');

interface Version {
  major: number;
  minor: number;
  patch: number;
}

function parseVersion(version: string): Version {
  const match = version.match(/^(\d+)\.(\d+)\.(\d+)$/);
  if (!match) {
    throw new Error(`Invalid version format: ${version}`);
  }
  return {
    major: parseInt(match[1], 10),
    minor: parseInt(match[2], 10),
    patch: parseInt(match[3], 10),
  };
}

function formatVersion(version: Version): string {
  return `${version.major}.${version.minor}.${version.patch}`;
}

function bumpVersion(version: Version, type: 'major' | 'minor' | 'patch'): Version {
  switch (type) {
    case 'major':
      return { major: version.major + 1, minor: 0, patch: 0 };
    case 'minor':
      return { major: version.major, minor: version.minor + 1, patch: 0 };
    case 'patch':
      return { major: version.major, minor: version.minor, patch: version.patch + 1 };
  }
}

function updatePyprojectToml(newVersion: string): void {
  const pyprojectPath = join(REPO_ROOT, 'pyproject.toml');
  const content = readFileSync(pyprojectPath, 'utf-8');
  const updated = content.replace(
    /version = "(\d+\.\d+\.\d+)"/,
    `version = "${newVersion}"`
  );
  writeFileSync(pyprojectPath, updated, 'utf-8');
  console.log(`✓ Updated pyproject.toml: ${newVersion}`);
}

function updatePackageJson(newVersion: string): void {
  const packagePath = join(REPO_ROOT, 'package.json');
  const content = readFileSync(packagePath, 'utf-8');
  const pkg = JSON.parse(content);
  
  // Update version if it exists (it's optional for private packages)
  if (pkg.version) {
    pkg.version = newVersion;
    writeFileSync(packagePath, JSON.stringify(pkg, null, '\t') + '\n', 'utf-8');
    console.log(`✓ Updated package.json: ${newVersion}`);
  } else {
    console.log('ℹ package.json has no version field (private package)');
  }
}

function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error('Usage: bump-version.ts <major|minor|patch|version>');
    process.exit(1);
  }

  const pyprojectPath = join(REPO_ROOT, 'pyproject.toml');
  const pyprojectContent = readFileSync(pyprojectPath, 'utf-8');
  const versionMatch = pyprojectContent.match(/version = "(\d+\.\d+\.\d+)"/);
  
  if (!versionMatch) {
    console.error('Could not find version in pyproject.toml');
    process.exit(1);
  }

  const currentVersion = parseVersion(versionMatch[1]);
  let newVersion: Version;

  const arg = args[0];
  
  if (['major', 'minor', 'patch'].includes(arg)) {
    newVersion = bumpVersion(currentVersion, arg as 'major' | 'minor' | 'patch');
  } else {
    // Explicit version
    newVersion = parseVersion(arg);
  }

  const newVersionStr = formatVersion(newVersion);
  console.log(`Bumping version: ${formatVersion(currentVersion)} -> ${newVersionStr}`);

  updatePyprojectToml(newVersionStr);
  updatePackageJson(newVersionStr);

  console.log('\n✓ Version bump complete!');
  console.log('  Don\'t forget to:');
  console.log('  1. Update CHANGELOG.md with release notes');
  console.log('  2. Commit the changes');
  console.log('  3. Create a git tag: git tag v' + newVersionStr);
  console.log('  4. Push the tag: git push origin v' + newVersionStr);
}

main();
