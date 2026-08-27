import { generateService } from '@umijs/openapi';

import config from '../openapi2ts.config.ts';

const response = await fetch(config.schemaPath);
if (!response.ok) {
  throw new Error(
    `OpenAPI schema request failed: ${response.status} ${response.statusText}`,
  );
}

const schema = await response.json();
const httpMethods = new Set([
  'delete',
  'get',
  'head',
  'options',
  'patch',
  'post',
  'put',
  'trace',
]);
const operations = Object.values(schema.paths ?? {}).flatMap((pathItem) =>
  Object.entries(pathItem ?? {})
    .filter(([method]) => httpMethods.has(method.toLowerCase()))
    .map(([, operation]) => operation),
);
if (
  operations.some((operation) => typeof operation?.operationId !== 'string')
) {
  throw new Error('Every OpenAPI operation must declare an operationId.');
}
const operationIds = operations.map((operation) => operation.operationId);
if (
  operationIds.length === 0 ||
  new Set(operationIds).size !== operationIds.length
) {
  throw new Error('OpenAPI operations must declare unique operationId values.');
}

await generateService(config);
console.log(`Generated ${operationIds.length} OpenAPI operations.`);
