import { App as AntApp, ConfigProvider } from 'antd';
import type { ReactNode } from 'react';

export function rootContainer(container: ReactNode) {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 8,
        },
      }}
    >
      <AntApp>{container}</AntApp>
    </ConfigProvider>
  );
}
