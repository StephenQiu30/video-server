import Alert from 'antd/es/alert';
import Button from 'antd/es/button';
import Card from 'antd/es/card';
import Progress from 'antd/es/progress';
import Skeleton from 'antd/es/skeleton';
import Space from 'antd/es/space';
import Tag from 'antd/es/tag';
import Typography from 'antd/es/typography';

import AnalysisPanel from '@/features/analysis/AnalysisPanel';
import type { DownloadStage, DownloadStatus } from '@/features/download/types';

import styles from './index.module.css';
import { useDownloadJob } from './useDownloadJob';

const statusLabels: Record<DownloadStatus, string> = {
  queued: '等待处理',
  running: '下载中',
  retry_wait: '等待重试',
  succeeded: '下载已完成',
  failed: '下载失败',
  cancelled: '任务已取消',
};

const stageLabels: Record<DownloadStage, string> = {
  revalidating: '重新校验格式',
  downloading: '下载媒体流',
  remuxing: '封装媒体文件',
  verifying: '验证文件',
  uploading: '保存文件',
};

const cancellable = new Set<DownloadStatus>([
  'queued',
  'running',
  'retry_wait',
]);

type DownloadJobPageProps = {
  jobId: string;
  pollIntervalMs?: number;
};

export default function DownloadJobPage({
  jobId,
  pollIntervalMs = 1500,
}: DownloadJobPageProps) {
  const state = useDownloadJob(jobId, pollIntervalMs);
  const { action, error, job, loading } = state;

  return (
    <main className={styles.page}>
      <a className={styles.back} href="/">
        ← 返回下载器
      </a>
      <Typography.Title level={1}>下载任务</Typography.Title>
      <Typography.Paragraph type="secondary">
        任务 ID：<code>{jobId}</code>
      </Typography.Paragraph>

      <Card className={styles.card} variant="borderless">
        {loading && !job ? <Skeleton active paragraph={{ rows: 4 }} /> : null}
        {error ? (
          <Alert
            action={
              !job ? (
                <Button onClick={state.retry} size="small">
                  重试
                </Button>
              ) : undefined
            }
            className={styles.alert}
            showIcon
            title={error}
            type="error"
          />
        ) : null}

        {job ? (
          <section aria-live="polite" className={styles.content}>
            <div className={styles.summary}>
              <div>
                <span className={styles.label}>状态</span>
                <Typography.Title level={3}>
                  {statusLabels[job.status]}
                </Typography.Title>
              </div>
              <Tag color={job.status === 'succeeded' ? 'green' : 'purple'}>
                第 {job.attempt} 次尝试
              </Tag>
            </div>

            <Progress
              percent={job.progress}
              status={progressStatus(job.status)}
            />
            <dl className={styles.details}>
              <div>
                <dt>当前阶段</dt>
                <dd>{job.stage ? stageLabels[job.stage] : '—'}</dd>
              </div>
              <div>
                <dt>更新时间</dt>
                <dd>{new Date(job.updated_at).toLocaleString('zh-CN')}</dd>
              </div>
            </dl>

            {job.status === 'failed' ? (
              <Alert
                showIcon
                title={`错误代码：${job.error_code ?? 'unknown_error'}`}
                type="error"
              />
            ) : null}

            <Space wrap>
              {cancellable.has(job.status) ? (
                <Button
                  aria-label="取消任务"
                  danger
                  loading={action === 'cancel'}
                  onClick={state.cancel}
                >
                  取消任务
                </Button>
              ) : null}
              {job.status === 'succeeded' ? (
                <Button
                  aria-label="获取文件"
                  loading={action === 'download'}
                  onClick={state.download}
                  type="primary"
                >
                  获取文件
                </Button>
              ) : null}
            </Space>
          </section>
        ) : null}
      </Card>
      {job?.status === 'succeeded' ? (
        <AnalysisPanel downloadId={job.id} pollIntervalMs={pollIntervalMs} />
      ) : null}
    </main>
  );
}

function progressStatus(
  status: DownloadStatus,
): 'active' | 'exception' | 'success' {
  if (status === 'failed') {
    return 'exception';
  }
  return status === 'succeeded' ? 'success' : 'active';
}
