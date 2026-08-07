export default [
  {
    component: './Home',
    icon: 'download',
    name: '新建下载',
    path: '/',
  },
  {
    component: './DownloadHistory',
    icon: 'history',
    name: '下载历史',
    path: '/downloads/history',
  },
  {
    component: './DownloadJob',
    hideInMenu: true,
    name: '下载任务',
    path: '/downloads/:jobId',
  },
  {
    component: './404',
    layout: false,
    path: '/*',
  },
];
