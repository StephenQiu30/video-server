import { type GenerateServiceProps, generateService } from '@umijs/openapi';

const config = {
  schemaPath:
    process.env.OPENAPI_SCHEMA_URL ?? 'http://127.0.0.1:19090/openapi.json',
  serversPath: './src',
  projectName: 'api',
  namespace: 'API',
  nullable: true,
  declareType: 'type',
  requestLibPath:
    "import { request, type RequestOptions } from '@/shared/api/request';",
  requestOptionsType: 'RequestOptions',
} satisfies GenerateServiceProps;

export default config;

await generateService(config);
