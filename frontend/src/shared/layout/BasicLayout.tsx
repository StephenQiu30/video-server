import { DownloadOutlined } from '@ant-design/icons';
import { ProLayout } from '@ant-design/pro-components';
import type { ReactNode } from 'react';

import { navigate } from '@/features/download/navigation';

import styles from './basic-layout.module.css';

type BasicLayoutProps = {
  active: 'new' | 'tasks';
  children: ReactNode;
};

const route = {
  path: '/',
  routes: [
    { path: '/', name: '新建下载' },
    { path: '/downloads', name: '任务' },
  ],
};

export default function BasicLayout({ active, children }: BasicLayoutProps) {
  const selectedPath = active === 'new' ? '/' : '/downloads';

  return (
    <ProLayout
      actionsRender={false}
      className={styles.layout}
      contentStyle={{ margin: 0, padding: 0 }}
      contentWidth="Fluid"
      footerRender={false}
      layout="top"
      locale="zh-CN"
      location={{ pathname: selectedPath }}
      logo={
        <span className={styles.brandMark}>
          <DownloadOutlined />
        </span>
      }
      menu={{ locale: false }}
      menuItemRender={(item, dom) =>
        item.path === '/' ? (
          <a
            href="/"
            onClick={(event) => {
              event.preventDefault();
              navigate('/');
            }}
          >
            {dom}
          </a>
        ) : (
          dom
        )
      }
      menuProps={{ selectedKeys: [selectedPath] }}
      onMenuHeaderClick={() => navigate('/')}
      route={route}
      title="视频下载器"
      token={{
        header: {
          colorBgHeader: '#fff',
          colorTextMenu: '#374151',
          colorTextMenuSelected: '#1677ff',
          heightLayoutHeader: 64,
        },
        pageContainer: { colorBgPageContainer: '#f8fafc' },
      }}
    >
      {children}
    </ProLayout>
  );
}
