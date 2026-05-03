import type { RequestConfig } from '@@/plugin-request/types';
import type { RunTimeLayoutConfig } from '@@/plugin-layout/types';
import { Space, Tag, Typography, message } from 'antd';
import { SafetyCertificateOutlined } from '@ant-design/icons';
import './global.css';

import { getCurrentUser } from './services/api';

export async function getInitialState(): Promise<{
  currentUser?: API.User;
  fetchUserInfo: () => Promise<API.User | undefined>;
}> {
  const fetchUserInfo = async () => {
    try {
      return await getCurrentUser();
    } catch {
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

export const layout: RunTimeLayoutConfig = () => {
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
        <Typography.Text strong>Stephen Video</Typography.Text>
      </div>
    ),
    rightContentRender: () => {
      return (
        <Space size={12}>
          <SafetyCertificateOutlined className="header-safe-icon" />
          <Tag color="processing">本地单用户模式</Tag>
        </Space>
      );
    },
    childrenRender: (children: JSX.Element) => <div className="page-shell">{children}</div>,
  };
};
