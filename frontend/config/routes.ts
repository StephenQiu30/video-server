export default [
  { path: '/', redirect: '/download' },
  { path: '/download', component: './Download' },
  { path: '/downloads/:jobId', component: './DownloadJob' },
  { path: '*', component: './404' },
];
