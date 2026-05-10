import { defineConfig } from '@umijs/max';

export default defineConfig({
  antd: {
    theme: {
      token: {
        borderRadius: 6,
        colorPrimary: '#1677ff',
        colorInfo: '#1677ff',
      },
    },
  },
  access: {},
  model: {},
  initialState: {},
  request: {},
  layout: {
    title: 'Stephen Video',
    logo: false,
    navTheme: 'light',
    layout: 'top',
    splitMenus: false,
    fixedHeader: true,
    fixSiderbar: true,
  },
  routes: [
    { path: '/', component: './Home' },
    { path: '/login', redirect: '/workspace' },
    { name: '下载工作台', path: '/workspace', component: './Workspace' },
    { name: '任务历史', path: '/tasks', component: './Tasks' },
    { path: '*', redirect: '/' },
  ],
  npmClient: 'npm',
});
