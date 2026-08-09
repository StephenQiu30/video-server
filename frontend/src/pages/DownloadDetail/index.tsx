import { ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from '@umijs/max';
import { Alert, Button, Result, Skeleton, Typography } from 'antd';
import { useCallback, useState } from 'react';

import AnalysisPanel from '@/components/AnalysisPanel';
import DownloadState from '@/components/DownloadState';
import MediaCover from '@/components/MediaCover';
import { useDownloadJob } from '@/hooks/useDownloadJob';
import type { AnalysisJob, MediaFormat } from '@/types/video';
import { formatDuration } from '@/utils/format';
import './index.less';

export default function DownloadDetailPage({
  pollIntervalMs = 1500,
}: {
  pollIntervalMs?: number;
}) {
  const navigate = useNavigate();
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId ?? '';

  const state = useDownloadJob(jobId, pollIntervalMs);
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(null);
  const handleAnalysisJob = useCallback((job: AnalysisJob | null) => {
    setAnalysisJob(job);
  }, []);
  const format = state.inspection?.formats.find(
    (item) => item.id === state.job?.format_id,
  );

  if (!jobId) {
    return (
      <Result
        status="404"
        subTitle="请从下载历史重新打开任务。"
        title={<Typography.Title level={1}>下载任务不存在</Typography.Title>}
      />
    );
  }

  if (state.loading && !state.job) {
    return (
      <div className="job-page">
        <div className="job-skeleton">
          <Skeleton.Image active style={{ height: 320, width: '100%' }} />
          <Skeleton active paragraph={{ rows: 6 }} />
        </div>
      </div>
    );
  }

  return (
    <div className="job-page">
      <Button
        className="job-back"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/')}
        type="text"
      >
        返回新建下载
      </Button>
      {state.error ? (
        <Alert
          className="job-alert"
          description={state.error}
          title="无法读取下载任务"
          showIcon
          type="error"
        />
      ) : null}
      {state.job ? (
        <>
          <section className="job-card">
            <div className="job-grid">
              <div className="job-media">
                <MediaCover
                  alt={`${state.inspection?.title ?? '视频'} 视频封面`}
                  durationSeconds={
                    state.inspection
                      ? state.inspection.duration_seconds
                      : undefined
                  }
                  platform={state.inspection?.extractor_key}
                  src={state.inspection?.thumbnail_url}
                />
                <Typography.Title level={2} className="job-title">
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
            </div>
          </section>
          {state.job.status === 'succeeded' ? (
            <AnalysisPanel
              downloadId={state.job.id}
              onJobChange={handleAnalysisJob}
            />
          ) : (
            <section className="job-card">
              <Typography.Text type="secondary">
                下载并验证完成后，可继续生成摘要与思维导图。
              </Typography.Text>
            </section>
          )}
          {analysisJob?.status === 'succeeded' ? <span hidden>分析已完成</span> : null}
        </>
      ) : null}
    </div>
  );
}

function formatLabel(format?: MediaFormat, duration?: number) {
  if (!format)
    return duration ? formatDuration(duration) : '正在读取媒体信息';
  return `${format.plan.width}×${format.plan.height} · ${format.plan.video_codec_family.toUpperCase()} + ${format.plan.audio_codec_family.toUpperCase()} · ${duration ? formatDuration(duration) : ''}`;
}