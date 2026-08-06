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
          borderRadius: 6,
          colorBgLayout: '#f8fafc',
          colorPrimary: '#1677ff',
          fontFamily:
            "Inter, 'PingFang SC', 'Microsoft YaHei', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        },
      },
    },
  },
  fastRefresh: true,
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
  openAPI: [
    {
      mock: false,
      projectName: 'video',
      requestLibPath: "import { request } from '@umijs/max'",
      schemaPath:
        process.env.OPENAPI_SCHEMA_URL ?? 'http://127.0.0.1:19090/openapi.json',
    },
  ],
  plugins: ['@umijs/max-plugin-openapi'],
  proxy,
  request: {
    dataField: '',
  },
  routes,
  title: '视频下载',
  utoopack: {},
});
