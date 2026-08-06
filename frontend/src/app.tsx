import AntApp from 'antd/es/app';
import ConfigProvider from 'antd/es/config-provider';
import { useEffect, useState } from 'react';

import NotFoundPage from '@/pages/404';
import DownloadJobPage from '@/pages/DownloadJob';
import HomePage from '@/pages/Home';

type AppProps = {
  path?: string;
};

const downloadPath =
  /^\/downloads\/([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})$/i;

export function App({ path }: AppProps) {
  const [browserPath, setBrowserPath] = useState(
    () => window.location.pathname,
  );
  const controlled = path !== undefined;

  useEffect(() => {
    if (controlled) {
      return;
    }
    const updatePath = () => setBrowserPath(window.location.pathname);
    window.addEventListener('popstate', updatePath);
    return () => window.removeEventListener('popstate', updatePath);
  }, [controlled]);

  const currentPath = path ?? browserPath;
  const match = downloadPath.exec(currentPath);
  const page =
    currentPath === '/' ? (
      <HomePage />
    ) : match ? (
      <DownloadJobPage jobId={match[1]} />
    ) : (
      <NotFoundPage />
    );

  return (
    <ConfigProvider
      theme={{
        token: {
          borderRadius: 10,
          colorPrimary: '#6956e8',
          fontFamily:
            "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        },
      }}
    >
      <AntApp>{page}</AntApp>
    </ConfigProvider>
  );
}
