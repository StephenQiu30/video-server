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
    customType(schema, namespace, original) {
      return schema?.type === 'string' && schema.format === 'binary'
        ? 'Blob'
        : original(schema, namespace);
    },
  },
};

export default config;
