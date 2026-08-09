/**
 * @name 代理的配置
 * @see 在生产环境 代理是无法生效的，所以这里没有生产环境的配置
 * @doc https://umijs.org/docs/guides/proxy
 */
export default {
  /**
   * @name 本地开发代理
   * @description 将本地前端请求转发到后端 FastAPI（127.0.0.1:8101）。
   * 生产环境由 FastAPI 同源托管静态产物，无需代理。
   */
  dev: {
    '/api/': {
      target: 'http://127.0.0.1:8101',
      changeOrigin: true,
    },
    '/health/': {
      target: 'http://127.0.0.1:8101',
      changeOrigin: true,
    },
    '/docs': {
      target: 'http://127.0.0.1:8101',
      changeOrigin: true,
    },
    '/redoc': {
      target: 'http://127.0.0.1:8101',
      changeOrigin: true,
    },
    '/openapi.json': {
      target: 'http://127.0.0.1:8101',
      changeOrigin: true,
    },
  },
  test: {
    '/api/': {
      target: 'http://127.0.0.1:8101',
      changeOrigin: true,
    },
  },
  pre: {
    '/api/': {
      target: 'http://127.0.0.1:8101',
      changeOrigin: true,
    },
  },
};