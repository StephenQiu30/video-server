import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

const packageJson = JSON.parse(
  readFileSync(resolve(process.cwd(), 'package.json'), 'utf8'),
) as { dependencies: Record<string, string> };
const packageLock = JSON.parse(
  readFileSync(resolve(process.cwd(), 'package-lock.json'), 'utf8'),
) as { packages: Record<string, { version?: string }> };
const notices = readFileSync(
  resolve(process.cwd(), 'THIRD-PARTY-NOTICES.md'),
  'utf8',
);
const dockerfile = readFileSync(
  resolve(process.cwd(), '..', 'Dockerfile'),
  'utf8',
);

describe('GSAP supply-chain boundary', () => {
  it('pins the reviewed package versions', () => {
    expect(packageJson.dependencies.gsap).toBe('3.15.0');
    expect(packageJson.dependencies['@gsap/react']).toBe('2.1.2');
    expect(packageLock.packages['node_modules/gsap']?.version).toBe('3.15.0');
    expect(packageLock.packages['node_modules/@gsap/react']?.version).toBe(
      '2.1.2',
    );
  });

  it('records and ships the dependency governance notice', () => {
    expect(notices).toContain('GSAP 3.15.0 and @gsap/react 2.1.2');
    expect(notices).toContain('https://github.com/greensock/react/tree/2.1.2');
    expect(notices).toContain('https://gsap.com/community/standard-license/');
    expect(notices).toContain(
      'Copyright 2008-2026, GreenSock. All rights reserved.',
    );
    expect(notices).toContain(
      'Copyright 2025, GreenSock. All rights reserved.',
    );
    expect(notices).toContain('Update strategy:');
    expect(notices).toContain('Removal plan:');
    expect(dockerfile).toContain(
      '/workspace/frontend/THIRD-PARTY-NOTICES.md /app/frontend/THIRD-PARTY-NOTICES.md',
    );
  });
});
