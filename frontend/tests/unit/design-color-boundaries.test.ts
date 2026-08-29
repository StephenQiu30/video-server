import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';

import { describe, expect, it } from 'vitest';

const businessRoots = ['src/app', 'src/components'];
const sourceExtensions = new Set(['.ts', '.tsx']);
const hardcodedColor =
  /#[\da-f]{3,8}\b|\b(?:rgb|hsl|oklch|lab|lch)a?\([^)]*\)/gi;
const paletteUtility =
  /\b(?:bg|text|border|ring|fill|stroke)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}(?:\/\d{1,3})?/g;
const chartUtility = /\b(?:bg|text|border|ring|fill|stroke)-chart-[1-5]\b/g;

function collectBusinessSources(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (target === path.join('src', 'components', 'ui')) return [];
      return collectBusinessSources(target);
    }
    return sourceExtensions.has(path.extname(entry.name)) ? [target] : [];
  });
}

describe('design color boundaries', () => {
  it('keeps business pages on semantic and component-default colors', () => {
    const findings = businessRoots
      .flatMap(collectBusinessSources)
      .flatMap((file) => {
        const source = readFileSync(file, 'utf8');
        return [hardcodedColor, paletteUtility, chartUtility].flatMap((rule) =>
          [...source.matchAll(rule)].map(
            (match) => `${file}: ${String(match[0])}`,
          ),
        );
      });

    expect(findings).toEqual([]);
  });

  it('uses the official shadcn neutral chart palette in both themes', () => {
    const globals = readFileSync('src/app/globals.css', 'utf8');
    const officialTokens = [
      'oklch(0.646 0.222 41.116)',
      'oklch(0.6 0.118 184.704)',
      'oklch(0.398 0.07 227.392)',
      'oklch(0.828 0.189 84.429)',
      'oklch(0.769 0.188 70.08)',
      'oklch(0.488 0.243 264.376)',
      'oklch(0.696 0.17 162.48)',
      'oklch(0.627 0.265 303.9)',
      'oklch(0.645 0.246 16.439)',
    ];

    for (const token of officialTokens) expect(globals).toContain(token);
  });
});
