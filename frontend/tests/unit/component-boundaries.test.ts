import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

import { describe, expect, it } from 'vitest';

const SOURCE_ROOT = path.join(process.cwd(), 'src');
const UI_ROOT = path.join(SOURCE_ROOT, 'components', 'ui');
const RAW_PRIMITIVE = /<(?:button|img|input|select|textarea)(?:\s|>)/;
const DIRECT_RADIX_IMPORT = /from\s+['"](?:@radix-ui\/[^'"]+|radix-ui)['"]/;

describe('component boundaries', () => {
  it('keeps native controls and Radix primitives inside shadcn/ui', async () => {
    const violations: string[] = [];
    for (const file of await sourceFiles(SOURCE_ROOT)) {
      if (!file.endsWith('.tsx') || file.startsWith(UI_ROOT)) continue;
      const source = await readFile(file, 'utf8');
      if (RAW_PRIMITIVE.test(source)) {
        violations.push(
          `${relative(file)} uses a raw interactive/image element`,
        );
      }
      if (DIRECT_RADIX_IMPORT.test(source)) {
        violations.push(`${relative(file)} imports Radix outside shadcn/ui`);
      }
    }

    expect(violations).toEqual([]);
  });
});

async function sourceFiles(directory: string): Promise<string[]> {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map((entry) => {
      const target = path.join(directory, entry.name);
      return entry.isDirectory()
        ? sourceFiles(target)
        : Promise.resolve([target]);
    }),
  );
  return nested.flat();
}

function relative(file: string): string {
  return path.relative(process.cwd(), file);
}
