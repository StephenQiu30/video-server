import { defineConfig } from '@umijs/max';
import defaultSettings from './defaultSettings';
import proxy from './proxy';
import routes from './routes';

export default defineConfig({
  antd: {
    appConfig: {},
    configProvider: {
      theme: {
        token: {
          colorError: '#1677ff',
          colorInfo: '#1677ff',
          colorPrimary: '#1677ff',
          colorSuccess: '#1677ff',
          colorWarning: '#1677ff',
        },
      },
    },
  },
  fastRefresh: true,
  favicons: ['/favicon.ico'],
  hash: true,
  layout: defaultSettings,
  locale: false,
  metas: [
    { charset: 'utf-8' },
    {
      content: 'width=device-width, initial-scale=1',
      name: 'viewport',
    },
  ],
  openAPI: {
    mock: false,
    namespace: 'API',
    projectName: 'video',
    requestLibPath: "import { request } from '@umijs/max'",
    schemaPath:
      process.env.OPENAPI_SCHEMA_URL ?? 'http://127.0.0.1:8101/openapi.json',
  },
  plugins: ['@umijs/max-plugin-openapi'],
  proxy,
  request: {
    dataField: '',
  },
  routes,
  title: '视频下载',
  utoopack: {},
});
