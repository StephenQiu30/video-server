const proxy = {
  '/api/': {
    changeOrigin: true,
    target: 'http://127.0.0.1:8101',
  },
  '/health/': {
    changeOrigin: true,
    target: 'http://127.0.0.1:8101',
  },
};

export default proxy;
