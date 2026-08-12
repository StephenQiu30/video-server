import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const globalsPath = resolve(process.cwd(), 'src/app/globals.css');

describe('global layout stability', () => {
  it('leaves scrollbar locking and compensation to the overlay primitives', () => {
    const styles = readFileSync(globalsPath, 'utf8');

    expect(styles).not.toContain('scrollbar-gutter:');
    expect(styles).toMatch(/body \{[\s\S]*overflow-y: scroll;/);
    expect(styles).not.toContain('data-scroll-locked');
    expect(styles).not.toContain('--removed-body-scroll-bar-size');
  });

  it('uses one compact top rhythm for authenticated inner pages', () => {
    const styles = readFileSync(globalsPath, 'utf8');

    expect(styles).toMatch(
      /\.inner-page \{[\s\S]*padding-block: 1\.5rem;[\s\S]*\}/,
    );
    expect(styles).toMatch(
      /@media \(min-width: 641px\)[\s\S]*\.inner-page \{[\s\S]*padding-block: 2rem;/,
    );
    expect(styles).toMatch(
      /@media \(min-width: 1024px\)[\s\S]*\.inner-page \{[\s\S]*padding-block: 2rem;/,
    );

    for (const path of [
      'src/app/account/page.tsx',
      'src/app/providers/page.tsx',
      'src/app/admin/users/page.tsx',
      'src/app/admin/providers/page.tsx',
      'src/app/admin/analytics/page.tsx',
      'src/components/download-history-view.tsx',
      'src/components/download-job-view.tsx',
    ]) {
      expect(readFileSync(resolve(process.cwd(), path), 'utf8')).toContain(
        'content-shell inner-page',
      );
    }
  });
});
