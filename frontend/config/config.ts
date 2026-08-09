// https://umijs.org/config/

import { defineConfig } from '@umijs/max';
import defaultSettings from './defaultSettings';
import proxy from './proxy';

import routes from './routes';

const { UMI_ENV = 'dev' } = process.env;

/**
 * @name 使用公共路径
 * @description 部署时的路径，如果部署在非根目录下，需要配置这个变量
 * @doc https://umijs.org/docs/api/config#publicpath
 */
const PUBLIC_PATH: string = '/';

export default defineConfig({
  /**
   * @name 显式注册插件
   * @description max 预设不自动加载，需在此注册以启用 `max openapi` 生成接口文件。
   */
  plugins: ['@umijs/max-plugin-openapi'],

  /**
   * @name openAPI 配置
   * @description 供 `@umijs/max-plugin-openapi` 读取，执行 `npm run openapi`（`max openapi`）
   * 时把后端 OpenAPI 契约重新生成到 src/services/video/。
   * @doc https://umijs.org/docs/max/api
   */
  openAPI: {
    requestLibPath: "import { request, type RequestOptions } from '@/utils/request';",
    schemaPath: 'http://127.0.0.1:8101/openapi.json',
    projectName: 'video',
    namespace: 'API',
  },

  /**
   * @name 开启 hash 模式
   * @description 让 build 之后的产物包含 hash 后缀。通常用于增量发布和避免浏览器加载缓存。
   * @doc https://umijs.org/docs/api/config#hash
   */
  hash: true,

  // esbuild 压缩重复 helper 校验要求（Umi 编译提示）
  esbuildMinifyIIFE: true,

  publicPath: PUBLIC_PATH,

  /**
   * @name 路由的配置，不在路由中引入的文件不会编译
   * @doc https://umijs.org/docs/guides/routes
   */
  routes,

  /**
   * @name moment 的国际化配置
   * @description 如果对国际化没有要求，打开之后能减少js的包大小
   * @doc https://umijs.org/docs/api/config#ignoremomentlocale
   */
  ignoreMomentLocale: true,

  /**
   * @name 代理配置
   * @description 本地开发时把请求代理到后端 FastAPI；build 后不生效。
   * @doc https://umijs.org/docs/guides/proxy
   */
  proxy: proxy[UMI_ENV as keyof typeof proxy],

  /**
   * @name 快速热更新配置
   * @description 一个不错的热更新组件，更新时可以保留 state
   */
  fastRefresh: true,

  /**
   * @name 路由预加载
   * @description 预加载路由资源，提升页面切换速度
   * @doc https://umijs.org/docs/api/config#routePrefetch
   */
  routePrefetch: {},

  /**
   * @name manifest 配置
   * @description 生成资源清单，配合 routePrefetch 使用
   */
  manifest: {},

  //============== 以下都是max的插件配置 ===============
  /**
   * @name 数据流插件
   * @@doc https://umijs.org/docs/max/data-flow
   */
  model: {},

  /**
   * 全局初始数据流，可以在插件之间共享数据。
   * @doc https://umijs.org/docs/max/data-flow
   */
  initialState: {},

  /**
   * @name layout 插件
   * @doc https://umijs.org/docs/max/layout-menu
   */
  title: '帧取',
  layout: {
    locale: true,
    ...defaultSettings,
  },

  /**
   * @name moment2dayjs 插件
   * @description 将项目中的 moment 替换为 dayjs
   * @doc https://umijs.org/docs/max/moment2dayjs
   */
  moment2dayjs: {
    preset: 'antd',
    plugins: ['duration', 'relativeTime'],
  },

  /**
   * @name 国际化插件
   * @doc https://umijs.org/docs/max/i18n
   */
  locale: {
    // default zh-CN
    default: 'zh-CN',
    antd: true,
    // default true, when it is true, will use `navigator.language` overwrite default
    baseNavigator: true,
  },

  /**
   * @name antd 插件
   * @description 内置了 babel import 插件
   * @doc https://umijs.org/docs/max/antd#antd
   */
  antd: {
    appConfig: {},
    configProvider: {
      cssVar: { key: 'ant' },
      theme: {
        token: {
          colorPrimary: '#1677FF',
        },
      },
    },
  },

  /**
   * @name 网络请求配置
   * @description 它基于 axios 和 ahooks 的 useRequest 提供了一套统一的网络请求和错误处理方案。
   * @doc https://umijs.org/docs/max/request
   */
  request: {},

  /**
   * @name 权限插件
   * @description 基于 initialState 的权限插件，必须先打开 initialState
   * @doc https://umijs.org/docs/max/access
   */
  access: {},

  /**
   * @name 静态导出
   * @description 为每个路由生成 HTML，配合后端 SPA 静态托管。
   */
  exportStatic: {},

  define: {
    'process.env.CI': process.env.CI,
  },
});
