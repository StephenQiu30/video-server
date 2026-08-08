'use client';

import '@ant-design/v5-patch-for-react-19';

import {
  BookOutlined,
  CloudDownloadOutlined,
  HistoryOutlined,
  PlayCircleFilled,
} from '@ant-design/icons';
import { ProConfigProvider, ProLayout } from '@ant-design/pro-components';
import { App, Button, ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const route = {
  path: '/',
  routes: [
    { path: '/', name: '下载', icon: <CloudDownloadOutlined /> },
    { path: '/history/', name: '历史记录', icon: <HistoryOutlined /> },
  ],
};

export default function ProAppShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname() ?? '/';

  return (
    <ConfigProvider locale={zhCN}>
      <App>
        <ProConfigProvider hashed={false}>
          <ProLayout
            className="app-shell"
            headerContentRender={false}
            layout="top"
            location={{ pathname }}
            logo={<PlayCircleFilled className="app-logo-icon" />}
            menuItemRender={(item, dom) => (
              <Link href={item.path ?? '/'}>{dom}</Link>
            )}
            menuProps={{ selectedKeys: [pathname] }}
            menu={{ type: 'group' }}
            rightContentRender={() => (
              <Button
                href="/docs"
                icon={<BookOutlined />}
                target="_blank"
                type="text"
              >
                使用说明
              </Button>
            )}
            route={route}
            title="帧取"
          >
            {children}
          </ProLayout>
        </ProConfigProvider>
      </App>
    </ConfigProvider>
  );
}
