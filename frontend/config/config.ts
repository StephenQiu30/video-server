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
          borderRadius: 8,
          colorBgContainer: '#ffffff',
          colorBgLayout: '#f7f7f8',
          colorBorder: '#e5e5e5',
          colorBorderSecondary: '#ededed',
          colorPrimary: '#171717',
          colorText: '#171717',
          colorTextSecondary: '#666666',
          controlHeight: 36,
          fontFamily:
            "Inter, 'PingFang SC', 'Microsoft YaHei', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        },
        components: {
          Button: {
            defaultShadow: 'none',
            primaryShadow: 'none',
          },
          Card: {
            boxShadowTertiary: 'none',
          },
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
