'use client';

import { useSearchParams } from 'next/navigation';

import DownloadJobView from '@/components/download-job-view';
import MissingDownload from '@/components/missing-download';

export default function DownloadRoute() {
  const searchParams = useSearchParams();
  const jobId = searchParams?.get('jobId')?.trim() ?? '';
  return jobId ? <DownloadJobView jobId={jobId} /> : <MissingDownload />;
}
