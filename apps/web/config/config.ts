import { defineConfig } from '@umijs/max';

export default defineConfig({
  antd: {
    theme: {
      token: {
        borderRadius: 6,
        colorPrimary: '#1677ff',
        colorInfo: '#1677ff',
        colorSuccess: '#0f8f64',
        colorWarning: '#c88116',
        colorError: '#d43f3a',
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
    { name: '合规边界', path: '/compliance', component: './Compliance' },
    { path: '*', redirect: '/' },
  ],
  npmClient: 'npm',
});
