import { describe, expect, it } from 'vitest';

import routes from '../../config/routes';

describe('routes', () => {
  it('declares the home, download-job, and catch-all routes', () => {
    expect(routes).toEqual([
      expect.objectContaining({
        component: './Home',
        name: '新建下载',
        path: '/',
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
