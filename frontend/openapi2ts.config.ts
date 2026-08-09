import type { GenerateServiceProps } from '@umijs/openapi';

const config: GenerateServiceProps = {
  schemaPath:
    process.env.OPENAPI_SCHEMA_URL ?? 'http://127.0.0.1:8101/openapi.json',
  serversPath: './src/services',
  projectName: 'video',
  requestImportStatement:
    "import { request, type RequestOptions } from '@/lib/request';",
  requestOptionsType: 'RequestOptions',
  namespace: 'API',
  enumStyle: 'string-literal',
  isCamelCase: true,
  nullable: false,
};

export default config;
