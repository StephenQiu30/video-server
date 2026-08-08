'use client';

import { ArrowLeftOutlined } from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import { Alert, Button, Skeleton, Typography } from 'antd';
import { useCallback, useState } from 'react';

import AnalysisPanel from '@/components/AnalysisPanel';
import DownloadState from '@/components/download-state';
import MediaCover from '@/components/media-cover';
import { useDownloadJob } from '@/hooks/useDownloadJob';
import type { AnalysisJob, MediaFormat } from '@/types/video';
import { formatDuration } from '@/utils/format';

export default function DownloadJobView({
  jobId,
  pollIntervalMs = 1500,
}: {
  jobId: string;
  pollIntervalMs?: number;
}) {
  const state = useDownloadJob(jobId, pollIntervalMs);
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(null);
  const handleAnalysisJob = useCallback((job: AnalysisJob | null) => {
    setAnalysisJob(job);
  }, []);
  const format = state.inspection?.formats.find(
    (item) => item.id === state.job?.format_id,
  );

  if (state.loading && !state.job) return <DownloadSkeleton />;

  return (
    <main className="content-page page-shell">
      <Button
        className="job-back"
        href="/"
        icon={<ArrowLeftOutlined />}
        type="text"
      >
        返回新建下载
      </Button>
      {state.error ? (
        <Alert
          className="workspace-alert"
          description={state.error}
          message="无法读取下载任务"
          showIcon
          type="error"
        />
      ) : null}
      {state.job ? (
        <>
          <ProCard>
            <section className="job-grid">
              <div>
                <MediaCover
                  alt={`${state.inspection?.title ?? '视频'} 视频封面`}
                  duration={
                    state.inspection
                      ? formatDuration(state.inspection.duration_seconds)
                      : undefined
                  }
                  platform={state.inspection?.extractor_key}
                  src={state.inspection?.thumbnail_url}
                />
                <Typography.Title className="job-title" level={1}>
                  {state.inspection?.title ?? '视频下载任务'}
                </Typography.Title>
                <Typography.Text type="secondary">
                  {formatLabel(format, state.inspection?.duration_seconds)}
                </Typography.Text>
              </div>
              <DownloadState
                action={state.action}
                format={format}
                job={state.job}
                onCancel={state.cancel}
                onDownload={state.download}
              />
            </section>
          </ProCard>
          {state.job.status === 'succeeded' ? (
            <AnalysisPanel
              downloadId={state.job.id}
              onJobChange={handleAnalysisJob}
            />
          ) : (
            <ProCard className="analysis-card">
              <Typography.Text type="secondary">
                下载并验证完成后，可继续生成摘要与思维导图。
              </Typography.Text>
            </ProCard>
          )}
          {analysisJob?.status === 'succeeded' ? (
            <span hidden>分析已完成</span>
          ) : null}
        </>
      ) : null}
    </main>
  );
}

function DownloadSkeleton() {
  return (
    <main className="page-shell skeleton-grid">
      <Skeleton.Image active style={{ height: 340, width: '100%' }} />
      <Skeleton active paragraph={{ rows: 6 }} />
    </main>
  );
}

function formatLabel(format?: MediaFormat, duration?: number) {
  if (!format) return duration ? formatDuration(duration) : '正在读取媒体信息';
  return `${format.plan.width}×${format.plan.height} · ${format.plan.video_codec_family.toUpperCase()} + ${format.plan.audio_codec_family.toUpperCase()} · ${duration ? formatDuration(duration) : ''}`;
}
