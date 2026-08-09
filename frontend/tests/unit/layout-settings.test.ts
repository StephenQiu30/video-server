import { describe, expect, it } from 'vitest';

import defaultSettings from '../../config/defaultSettings';

describe('Ant Design Pro 布局配置', () => {
  it('统一使用顶部导航和官方定宽内容区', () => {
    expect(defaultSettings).toMatchObject({
      contentWidth: 'Fixed',
      fixedHeader: false,
      layout: 'top',
      logo: '/logo.png',
      title: '帧取',
    });
    expect(defaultSettings.token).toMatchObject({
      bgLayout: '#fff',
      header: {
        colorBgHeader: '#fff',
      },
      pageContainer: {
        colorBgPageContainer: '#fff',
        colorBgPageContainerFixed: '#fff',
      },
    });
  });
});
