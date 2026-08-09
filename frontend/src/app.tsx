import type { Settings as LayoutSettings } from '@ant-design/pro-components';
import type { RunTimeLayoutConfig } from '@umijs/max';
import { Link } from '@umijs/max';
import React from 'react';

import defaultSettings from '../config/defaultSettings';

/**
 * @see https://umijs.org/docs/api/runtime-config#getinitialstate
 * 本项目为匿名应用，无需登录，直接返回布局设置。
 * */
export async function getInitialState(): Promise<{
  settings?: Partial<LayoutSettings>;
}> {
  return {
    settings: defaultSettings as Partial<LayoutSettings>,
  };
}

// ProLayout 支持的api https://procomponents.ant.design/components/layout
export const layout: RunTimeLayoutConfig = ({ initialState }) => {
  return {
    menuItemRender: (item, dom) => {
      if (item.path) {
        return (
          <Link to={item.path} prefetch>
            {dom}
          </Link>
        );
      }
      return dom;
    },
    actionsRender: () => [],
    // 关闭用户头像菜单
    avatarProps: undefined,
    footerRender: () => undefined,
    onPageChange: () => {},
    bgLayoutImgList: undefined,
    menuHeaderRender: undefined,
    ...initialState?.settings,
  };
};

export function rootContainer(container: React.ReactNode) {
  return <>{container}</>;
}
