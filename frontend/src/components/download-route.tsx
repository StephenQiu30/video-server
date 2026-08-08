'use client';

import { useSearchParams } from 'next/navigation';

import DownloadJobView from '@/components/download-job-view';

export default function DownloadRoute() {
  const jobId = useSearchParams()?.get('jobId');
  if (!jobId) {
    return (
      <main className="page-shell py-24">
        <h1 className="text-3xl font-semibold">下载任务不存在</h1>
        <p className="mt-3 text-muted-foreground">请从下载历史重新打开任务。</p>
      </main>
    );
  }
  return <DownloadJobView jobId={jobId} />;
}
