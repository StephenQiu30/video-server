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
});
