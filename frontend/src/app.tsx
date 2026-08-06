import { App as AntApp, ConfigProvider } from 'antd';
import { lazy, Suspense, useEffect, useState } from 'react';

const HomePage = lazy(() => import('@/pages/Home'));
const DownloadJobPage = lazy(() => import('@/pages/DownloadJob'));
const NotFoundPage = lazy(() => import('@/pages/404'));

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
          borderRadius: 6,
          colorBgLayout: '#f8fafc',
          colorPrimary: '#1677ff',
          fontFamily:
            "Inter, 'PingFang SC', 'Microsoft YaHei', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        },
      }}
    >
      <AntApp>
        <Suspense fallback={null}>{page}</Suspense>
      </AntApp>
    </ConfigProvider>
  );
}
