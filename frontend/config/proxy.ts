const target = process.env.VIDEO_API_PROXY_TARGET;

const apiProxy = target
  ? {
      '/api/': {
        target,
        changeOrigin: true,
      },
    }
  : {};

export default {
  dev: apiProxy,
  test: apiProxy,
};
