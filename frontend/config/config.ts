import { defineConfig } from '@umijs/max';
import proxy from './proxy';
import routes from './routes';

const { UMI_ENV = 'dev' } = process.env;
const openApiSchemaPath = process.env.OPENAPI_SCHEMA_URL;
const hasOpenApiSchema = Boolean(openApiSchemaPath);
const openApiConfig = hasOpenApiSchema
  ? {
      openAPI: [
        {
          requestLibPath: "import { request } from '@umijs/max'",
          schemaPath: openApiSchemaPath,
          projectName: 'video',
          mock: false,
        },
      ],
    }
  : {};

export default defineConfig({
  hash: true,
  esbuildMinifyIIFE: true,
  routes,
  proxy: proxy[UMI_ENV as keyof typeof proxy],
  fastRefresh: true,
  antd: {},
  request: {},
  reactQuery: {},
  title: '公开视频下载器',
  plugins: hasOpenApiSchema ? ['@umijs/max-plugin-openapi'] : [],
  ...openApiConfig,
  define: {
    'process.env.VIDEO_API_BASE_URL': process.env.VIDEO_API_BASE_URL,
  },
});
