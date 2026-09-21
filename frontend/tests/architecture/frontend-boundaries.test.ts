import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const root = resolve(process.cwd(), 'src');

function requestBoundaryViolations(text: string, filename: string): string[] {
  const source = ts.createSourceFile(
    filename,
    text,
    ts.ScriptTarget.Latest,
    true,
  );
  const violations: string[] = [];
  function visit(node: ts.Node) {
    if (
      (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) &&
      node.moduleSpecifier &&
      ts.isStringLiteral(node.moduleSpecifier)
    ) {
      const name = node.moduleSpecifier.text;
      const resolved = name.startsWith('@/')
        ? resolve(root, name.slice(2))
        : resolve(filename, '..', name);
      if (
        name === 'axios' ||
        resolved.replace(/\.tsx?$/, '') === resolve(root, 'lib/request')
      )
        violations.push(name);
    }
    if (ts.isCallExpression(node)) {
      const callee = node.expression;
      if (ts.isIdentifier(callee) && callee.text === 'fetch')
        violations.push('fetch');
      if (
        ts.isPropertyAccessExpression(callee) &&
        ['window', 'globalThis'].includes(callee.expression.getText(source)) &&
        callee.name.text === 'fetch'
      )
        violations.push('fetch');
    }
    if (
      ts.isNewExpression(node) &&
      node.expression.getText(source) === 'XMLHttpRequest'
    )
      violations.push('XMLHttpRequest');
    ts.forEachChild(node, visit);
  }
  visit(source);
  return violations;
}

function sources(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name);
    return entry.isDirectory()
      ? sources(path)
      : /\.tsx?$/.test(entry.name)
        ? [path]
        : [];
  });
}

describe('frontend project boundaries', () => {
  it('keeps the documented source directories without parallel DTO or service layers', () => {
    const directories = readdirSync(root, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .sort();
    expect(directories).toEqual(['api', 'app', 'components', 'hooks', 'lib']);
  });

  it('keeps component and hook requests behind generated API or shared orchestration', () => {
    for (const file of [
      ...sources(resolve(root, 'components')),
      ...sources(resolve(root, 'hooks')),
    ]) {
      expect(
        requestBoundaryViolations(readFileSync(file, 'utf8'), file),
        file,
      ).toEqual([]);
    }
  });

  it.each([
    "import axios from 'axios';",
    "import { request } from '@/lib/request';",
    "export { request } from '../../lib/request';",
    "fetch('/api/users');",
    "globalThis.fetch('/api/users');",
    'new XMLHttpRequest();',
  ])('detects direct HTTP bypass: %s', (code) => {
    expect(
      requestBoundaryViolations(
        code,
        resolve(root, 'components/example/view.tsx'),
      ),
    ).not.toEqual([]);
  });

  it('allows generated clients and error display helpers', () => {
    expect(
      requestBoundaryViolations(
        "import { getCurrentUser } from '@/api/auth'; import { displayError } from '@/lib/request-error';",
        resolve(root, 'components/example/view.tsx'),
      ),
    ).toEqual([]);
  });
});
