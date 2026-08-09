import {
  LogoutOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import type { Settings as LayoutSettings } from '@ant-design/pro-components';
import type { RunTimeLayoutConfig } from '@umijs/max';
import { history, Link } from '@umijs/max';
import type { MenuProps } from 'antd';
import { Dropdown } from 'antd';
import React from 'react';

import defaultSettings from '../config/defaultSettings';
import { type AuthUser, getCurrentUser, logout } from './services/auth';

export type InitialState = {
  currentUser?: AuthUser;
  fetchCurrentUser: () => Promise<AuthUser | undefined>;
  settings?: Partial<LayoutSettings>;
};

async function fetchCurrentUser(): Promise<AuthUser | undefined> {
  try {
    return await getCurrentUser();
  } catch {
    return undefined;
  }
}

export async function getInitialState(): Promise<InitialState> {
  return {
    currentUser: await fetchCurrentUser(),
    fetchCurrentUser,
    settings: defaultSettings as Partial<LayoutSettings>,
  };
}

export const layout: RunTimeLayoutConfig = ({
  initialState,
  setInitialState,
}) => {
  const currentUser = initialState?.currentUser;
  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      await setInitialState({
        currentUser: undefined,
        fetchCurrentUser,
        settings: initialState?.settings,
      });
      history.replace('/user/login');
    }
  };
  const accountMenu: MenuProps = {
    items: [
      {
        key: 'profile',
        icon: <SettingOutlined />,
        label: '个人资料',
      },
      ...(currentUser?.role === 'admin'
        ? [
            {
              key: 'users',
              icon: <TeamOutlined />,
              label: '用户管理',
            },
          ]
        : []),
      { type: 'divider' },
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: '退出登录',
      },
    ],
    onClick: ({ key }) => {
      if (key === 'logout') {
        void handleLogout();
      } else if (key === 'profile') {
        history.push('/account');
      } else if (key === 'users') {
        history.push('/admin/users');
      }
    },
  };

  return {
    menuItemRender: (item, dom) =>
      item.path ? (
        <Link to={item.path} prefetch>
          {dom}
        </Link>
      ) : (
        dom
      ),
    actionsRender: () => [],
    avatarProps: currentUser
      ? {
          icon: <UserOutlined />,
          size: 'small',
          title: currentUser.username,
          render: (_props, avatar) => (
            <Dropdown menu={accountMenu} placement="bottomRight">
              <span className="account-entry">{avatar}</span>
            </Dropdown>
          ),
        }
      : undefined,
    footerRender: () => undefined,
    onPageChange: () => {
      const path = history.location.pathname;
      if (!currentUser && !path.startsWith('/user/')) {
        const redirect = `${path}${history.location.search}`;
        history.replace(`/user/login?redirect=${encodeURIComponent(redirect)}`);
      }
    },
    bgLayoutImgList: undefined,
    menuHeaderRender: undefined,
    ...initialState?.settings,
  };
};

export function rootContainer(container: React.ReactNode) {
  return <>{container}</>;
}
