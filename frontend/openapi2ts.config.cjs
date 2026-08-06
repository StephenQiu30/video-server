/** @type {import('@umijs/openapi').GenerateServiceProps} */
module.exports = {
  schemaPath:
    process.env.OPENAPI_SCHEMA_URL ?? 'http://127.0.0.1:19090/openapi.json',
  serversPath: './src/generated',
  projectName: 'api',
  namespace: 'API',
  nullable: true,
  declareType: 'type',
  requestLibPath:
    "import { request, type RequestOptions } from '@/shared/api/client';",
  requestOptionsType: 'RequestOptions',
  hook: {
    customFunctionName({ method, operationId, path }) {
      const source =
        operationId?.replace(/_(?:api|health)_.+$/, '') ?? `${method}_${path}`;
      return source.replace(/[^a-zA-Z0-9]+(.)/g, (_, letter) =>
        letter.toUpperCase(),
      );
    },
  },
};
