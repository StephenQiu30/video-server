/**
 * @name umi 的路由配置
 * @description 只支持 path,component,routes,redirect,wrappers,name,icon 的配置
 * @param path  path 只支持两种占位符配置，第一种是动态参数 :id 的形式，第二种是 * 通配符，通配符只能出现路由字符串的最后。
 * @param component 配置 location 和 path 匹配后用于渲染的 React 组件路径。可以是绝对路径，也可以是相对路径，如果是相对路径，会从 src/pages 开始找起。
 * @param routes 配置子路由，通常在需要为多个路径增加 layout 组件时使用。
 * @param redirect 配置路由跳转
 * @param wrappers 配置路由组件的包装组件，通过包装组件可以为当前的路由组件组合进更多的功能。
 * @param name 配置路由的标题，默认读取国际化文件 menu.ts 中 menu.xxxx 的值
 * @doc https://umijs.org/docs/guides/routes
 */
export default [
  {
    path: '/user/login',
    component: './User/Login',
    layout: false,
  },
  {
    path: '/user/register',
    component: './User/Register',
    layout: false,
  },
  {
    path: '/',
    name: 'download',
    icon: 'cloudDownload',
    component: './Download',
  },
  {
    path: '/history',
    name: 'history',
    icon: 'history',
    component: './History',
  },
  {
    path: '/account',
    name: 'account',
    hideInMenu: true,
    component: './Account',
  },
  {
    path: '/admin/users',
    name: 'user-management',
    icon: 'team',
    access: 'canAdmin',
    component: './AdminUsers',
  },
  {
    path: '/downloads/:jobId',
    name: 'download-detail',
    hideInMenu: true,
    component: './DownloadDetail',
  },
  {
    path: '*',
    component: './404',
    layout: false,
  },
];
