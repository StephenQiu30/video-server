'use client';

import { useSearchParams } from 'next/navigation';

import AnalysisPanel from '@/components/analysis/analysis-panel';
import { BackLink } from '@/components/layout/back-link';
import DownloadJobView from '@/components/downloads/download-job-view';
import MissingDownload from '@/components/downloads/missing-download';

export default function DownloadRoute() {
  const searchParams = useSearchParams();
  const jobId = searchParams?.get('jobId')?.trim() ?? '';
  const analysisId = searchParams?.get('analysisId')?.trim() || undefined;
  if (jobId) return <DownloadJobView jobId={jobId} analysisId={analysisId} />;
  if (analysisId)
    return (
      <div className="inner-page">
        <BackLink fallbackHref="/history" />
        <AnalysisPanel
          downloadId={analysisId}
          analysisId={analysisId}
          playbackUnavailableReason="来源视频不可用，仍可查看分析结果。"
        />
      </div>
    );
  return <MissingDownload />;
}
