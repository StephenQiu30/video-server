import { Skeleton } from 'antd';
import { Suspense } from 'react';

import DownloadRoute from '@/components/download-route';

export const metadata = { title: '下载任务' };

export default function DownloadPage() {
  return (
    <Suspense
      fallback={
        <div className="page-shell content-page">
          <Skeleton active paragraph={{ rows: 8 }} />
        </div>
      }
    >
      <DownloadRoute />
    </Suspense>
  );
}
