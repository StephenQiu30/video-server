import type { GenerateServiceProps } from '@umijs/openapi';

const config: GenerateServiceProps = {
  schemaPath:
    process.env.OPENAPI_SCHEMA_URL ?? 'http://127.0.0.1:8111/openapi.json',
  serversPath: './src',
  projectName: 'api',
  requestImportStatement:
    "import { request, type RequestOptions } from '@/lib/request';",
  requestOptionsType: 'RequestOptions',
  namespace: 'API',
  enumStyle: 'string-literal',
  isCamelCase: true,
  nullable: false,
  hook: {
    afterOpenApiDataInited(document) {
      // The generator selects 200/201/default only. Preserve the code-first
      // 202 schema for its type selection; this does not change the HTTP API.
      for (const path of Object.values(document.paths)) {
        for (const method of [
          'get',
          'post',
          'put',
          'patch',
          'delete',
        ] as const) {
          const responses = path?.[method]?.responses;
          if (responses?.['202'] && !responses['200'] && !responses['201']) {
            responses['200'] = responses['202'];
          }
        }
      }
      return document;
    },
    customType(schema, namespace, original) {
      return schema?.type === 'string' && schema.format === 'binary'
        ? 'Blob'
        : original(schema, namespace);
    },
  },
};

export default config;
