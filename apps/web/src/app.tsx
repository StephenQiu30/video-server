import type { RequestConfig } from '@@/plugin-request/types';
import type { RunTimeLayoutConfig } from '@@/plugin-layout/types';
import { Space, Tag, Typography, message } from 'antd';
import { SafetyCertificateOutlined } from '@ant-design/icons';
import './global.css';

export async function getInitialState(): Promise<{
  mode: 'local-single-user';
}> {
  return {
    mode: 'local-single-user',
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
        colorBgHeader: '#ffffff',
      },
      sider: {
        colorMenuBackground: '#ffffff',
        colorBgCollapsedButton: '#ffffff',
      },
    },
    menuHeaderRender: () => (
      <div className="brand-lockup">
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
