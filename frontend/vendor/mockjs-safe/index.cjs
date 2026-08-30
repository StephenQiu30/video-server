'use strict';

const forbiddenKeys = new Set(['__proto__', 'constructor', 'prototype']);

const Random = {
  extend(extensions) {
    if (!extensions || typeof extensions !== 'object') {
      throw new TypeError('Random extensions must be an object.');
    }
    for (const [name, extension] of Object.entries(extensions)) {
      if (forbiddenKeys.has(name) || typeof extension !== 'function') {
        throw new TypeError('Random extension is invalid.');
      }
      Object.defineProperty(Random, name, {
        configurable: false,
        enumerable: true,
        value: extension,
        writable: false,
      });
    }
  },
  pick(values) {
    if (!Array.isArray(values) || values.length === 0) return undefined;
    return values[Math.floor(Math.random() * values.length)];
  },
};

function mock() {
  throw new Error(
    'Mock generation is disabled. This compatibility package only supports OpenAPI service generation.',
  );
}

module.exports = { Random, mock };
