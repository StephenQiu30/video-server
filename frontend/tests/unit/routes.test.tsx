import { describe, expect, it } from 'vitest';

import routes from '../../config/routes';

describe('routes', () => {
  it('declares the home, history, download-job, and catch-all routes', () => {
    expect(routes).toEqual([
      expect.objectContaining({
        component: './Home',
        name: '新建下载',
        path: '/',
      }),
      expect.objectContaining({
        component: './DownloadHistory',
        icon: 'history',
        name: '下载历史',
        path: '/downloads/history',
      }),
      expect.objectContaining({
        component: './DownloadJob',
        hideInMenu: true,
        path: '/downloads/:jobId',
      }),
      expect.objectContaining({
        component: './404',
        layout: false,
        path: '/*',
      }),
    ]);
  });
});
