import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';

test('concurrent sync requests preserve their own authorization transaction', async () => {
  let listener;
  const sent = [];
  runInNewContext(await readFile(new URL('./service-worker.js', import.meta.url), 'utf8'), {
    crypto: { randomUUID: () => crypto.randomUUID() },
    chrome: {
      cookies: { getAll: async () => [] },
      runtime: {
        onMessage: { addListener: (callback) => { listener = callback; } },
        sendNativeMessage: (_host, message, callback) => {
          sent.push(message);
          callback({ ok: true, provider: message.provider, revision: message.revision });
        },
      },
    },
  });
  const transactionIds = ['a'.repeat(32), 'b'.repeat(32)];
  const responses = await Promise.all(transactionIds.map((transactionId) => new Promise((resolve) => {
    assert.equal(listener({ type: 'sync', provider: 'douyin', transactionId }, {}, resolve), true);
  })));
  assert.ok(responses.every((response) => response.ok));
  assert.deepEqual(sent.map((message) => message.transaction_id), transactionIds);
  assert.equal(listener({ type: 'sync', provider: 'douyin' }, {}, () => {}), false);
});
