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

  it('uses the official blue chart palette in both themes', () => {
    const globals = readFileSync('src/app/globals.css', 'utf8');
    const officialTokens = [
      'oklch(0.546 0.245 262.881)',
      'oklch(0.707 0.165 254.624)',
      'oklch(0.488 0.243 264.376)',
      'oklch(0.809 0.105 251.813)',
      'oklch(0.623 0.214 259.815)',
      'oklch(0.882 0.059 254.128)',
    ];

    for (const token of officialTokens) expect(globals).toContain(token);
  });
});
