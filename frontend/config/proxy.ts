const proxy = {
  '/api/': {
    changeOrigin: true,
    target: 'http://127.0.0.1:19090',
  },
  '/health/': {
    changeOrigin: true,
    target: 'http://127.0.0.1:19090',
  },
};

export default proxy;
