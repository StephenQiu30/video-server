import { describe, expect, it } from 'vitest';

import config from '../../openapi2ts.config';

describe('code-first accepted response generation', () => {
  it('selects the real 202 response schema without replacing 200/201 schemas', () => {
    const accepted = {
      description: 'Accepted',
      content: {
        'application/json': {
          schema: { $ref: '#/components/schemas/ApiResponseIntentResponse_' },
        },
      },
    };
    const created = { description: 'Created' };
    const document = {
      openapi: '3.0.3',
      info: { title: 'Fixture', version: '1' },
      paths: {
        '/intents': { post: { responses: { '202': accepted } } },
        '/jobs': { post: { responses: { '201': created, '202': accepted } } },
      },
    };
    const result = config.hook?.afterOpenApiDataInited?.(document);
    expect(result?.paths['/intents']?.post?.responses['200']).toBe(accepted);
    expect(result?.paths['/intents']?.post?.responses['202']).toBe(accepted);
    expect(result?.paths['/jobs']?.post?.responses['200']).toBeUndefined();
    expect(result?.paths['/jobs']?.post?.responses['201']).toBe(created);
  });
});
