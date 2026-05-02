import type { RequestConfig } from '@@/plugin-request/types';
import type { RunTimeLayoutConfig } from '@@/plugin-layout/types';
import { history } from '@@/core/history';
import { Avatar, Button, Space, Typography, message } from 'antd';
import { LogoutOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import './global.css';

import { getCurrentUser, getToken, logout } from './services/api';

export async function getInitialState(): Promise<{
  currentUser?: API.User;
  fetchUserInfo: () => Promise<API.User | undefined>;
}> {
  const fetchUserInfo = async () => {
    if (!getToken()) {
      return undefined;
    }
    try {
      return await getCurrentUser();
    } catch {
      logout();
      return undefined;
    }
  };
  return {
    currentUser: await fetchUserInfo(),
    fetchUserInfo,
  };
}

export const request: RequestConfig = {
  errorConfig: {
    errorThrower: (response: { code?: string; message?: string }) => {
      const data = response as { code?: string; message?: string };
      if (data?.code || data?.message) {
        throw new Error(data.message || data.code || '请求失败');
      }
    },
    errorHandler: (error: Error) => {
      message.error(error.message || '请求失败，请稍后重试');
    },
  },
};

export const layout: RunTimeLayoutConfig = ({ initialState, setInitialState }) => {
  return {
    layout: 'top',
    splitMenus: false,
    token: {
      header: {
        colorBgHeader: '#f7f8fb',
      },
      sider: {
        colorMenuBackground: '#f7f8fb',
        colorBgCollapsedButton: '#ffffff',
      },
    },
    menuHeaderRender: () => (
      <div className="brand-lockup">
        <div className="brand-mark">SV</div>
        <div>
          <Typography.Text strong>Stephen Video</Typography.Text>
          <Typography.Text type="secondary" className="brand-subtitle">
            SaaS Console
          </Typography.Text>
        </div>
      </div>
    ),
    rightContentRender: () => {
      if (!initialState?.currentUser) {
        return (
          <Button type="primary" onClick={() => history.push('/login')}>
            登录
          </Button>
        );
      }
      return (
        <Space size={12}>
          <SafetyCertificateOutlined className="header-safe-icon" />
          <Avatar size={30}>{initialState.currentUser.display_name?.[0] || 'U'}</Avatar>
          <Typography.Text>{initialState.currentUser.display_name || initialState.currentUser.email}</Typography.Text>
          <Button
            icon={<LogoutOutlined />}
            onClick={() => {
              logout();
              setInitialState({ ...initialState, currentUser: undefined });
              history.push('/login');
            }}
          />
        </Space>
      );
    },
    onPageChange: () => {
      const { location } = history;
      if (!getToken() && location.pathname !== '/login') {
        history.push('/login');
      }
    },
    childrenRender: (children: JSX.Element) => <div className="page-shell">{children}</div>,
  };
};
