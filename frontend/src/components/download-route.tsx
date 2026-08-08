'use client';

import { Result, Typography } from 'antd';
import { useSearchParams } from 'next/navigation';

import DownloadJobView from '@/components/download-job-view';

export default function DownloadRoute() {
  const jobId = useSearchParams()?.get('jobId');
  if (!jobId) {
    return (
      <main className="page-shell content-page">
        <Result
          status="404"
          subTitle="请从下载历史重新打开任务。"
          title={<Typography.Title level={1}>下载任务不存在</Typography.Title>}
        />
      </main>
    );
  }
  return <DownloadJobView jobId={jobId} />;
}
