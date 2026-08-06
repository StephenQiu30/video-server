import { describe, expect, it } from 'vitest';
import routes from '../../config/routes';

describe('应用路由', () => {
  it('只暴露 MVP 规定的根路由、下载页、任务页和 404', () => {
    expect(routes).toEqual([
      { path: '/', redirect: '/download' },
      { path: '/download', component: './Download' },
      { path: '/downloads/:jobId', component: './DownloadJob' },
      { path: '*', component: './404' },
    ]);
  });
});
