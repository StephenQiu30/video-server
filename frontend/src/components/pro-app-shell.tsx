'use client';

import '@ant-design/v5-patch-for-react-19';

import {
  BookOutlined,
  CloudDownloadOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import { ProConfigProvider, ProLayout } from '@ant-design/pro-components';
import { App, Button, ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

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
  const [collapsed, setCollapsed] = useState(true);

  useEffect(() => {
    setCollapsed(Boolean(pathname));
  }, [pathname]);

  const logo = (
    <img
      alt="帧取 Logo"
      className="app-logo"
      height={32}
      src="/logo.svg"
      width={32}
    />
  );

  return (
    <ConfigProvider locale={zhCN}>
      <App>
        <ProConfigProvider hashed={false}>
          <ProLayout
            className="app-shell"
            collapsed={collapsed}
            onCollapse={setCollapsed}
            headerContentRender={false}
            layout="top"
            location={{ pathname }}
            logo={logo}
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
