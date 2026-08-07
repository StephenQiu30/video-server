import { CheckCircleFilled } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { useParams } from '@umijs/max';
import { Alert, Button, Flex, Result, Skeleton, Tag, Typography } from 'antd';
import { useCallback, useState } from 'react';

import AnalysisPanel from '@/components/AnalysisPanel';
import { useDownloadJob } from '@/hooks/useDownloadJob';
import type { AnalysisJob, MediaFormat } from '@/types/video';
import { formatDuration } from '@/utils/format';
import MediaSidebar from './components/MediaSidebar';
import styles from './index.module.css';

type DownloadJobPageProps = {
  jobId: string;
  pollIntervalMs?: number;
};

export default function DownloadJobRoute() {
  const { jobId } = useParams<{ jobId: string }>();
  if (!jobId) {
    return <Result status="404" title="下载任务不存在" />;
  }
  return <DownloadJobPage jobId={jobId} />;
}

export function DownloadJobPage({
  jobId,
  pollIntervalMs = 1500,
}: DownloadJobPageProps) {
  const state = useDownloadJob(jobId, pollIntervalMs);
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(null);
  const handleAnalysisJob = useCallback((current: AnalysisJob | null) => {
    setAnalysisJob(current);
  }, []);
  const format = state.inspection?.formats?.find(
    (item) => item.id === state.job?.format_id,
  );
  const title = state.inspection?.title ?? '下载任务';

  return (
    <PageContainer
      breadcrumb={{
        items: [{ title: '新建下载', href: '/' }, { title: '任务' }],
      }}
      className={styles.container}
      subTitle={
        state.inspection
          ? metadata(state.inspection.duration_seconds, format)
          : undefined
      }
      tags={
        <Flex gap={8} wrap>
          {state.job?.status === 'succeeded' ? (
            <Tag color="blue" icon={<CheckCircleFilled />}>
              文件已验证
            </Tag>
          ) : null}
          {analysisJob?.status === 'succeeded' ? (
            <Tag color="blue" icon={<CheckCircleFilled />}>
              分析已完成
            </Tag>
          ) : null}
        </Flex>
      }
      title={title}
    >
      <main className={styles.page}>
        {state.error ? (
          <Alert
            action={
              !state.job ? (
                <Button onClick={state.retry}>重试</Button>
              ) : undefined
            }
            className={styles.alert}
            showIcon
            title={state.error}
            type="info"
          />
        ) : null}
        {state.inspectionError ? (
          <Alert
            className={styles.alert}
            showIcon
            title={state.inspectionError}
            type="info"
          />
        ) : null}

        {state.loading && !state.job ? (
          <div className={styles.loading}>
            <Skeleton active paragraph={{ rows: 8 }} />
          </div>
        ) : null}

        {state.job ? (
          <div className={styles.workspace}>
            <aside className={styles.mediaColumn}>
              <MediaSidebar
                action={state.action}
                analysisResult={analysisJob?.result ?? null}
                inspection={state.inspection}
                job={state.job}
                onCancel={state.cancel}
                onDownload={state.download}
              />
            </aside>
            <section className={styles.analysisColumn}>
              {state.job.status === 'succeeded' ? (
                <AnalysisPanel
                  downloadId={state.job.id}
                  onJobChange={handleAnalysisJob}
                  pollIntervalMs={pollIntervalMs}
                />
              ) : (
                <WaitingForDownload />
              )}
            </section>
          </div>
        ) : null}
      </main>
    </PageContainer>
  );
}

function WaitingForDownload() {
  return (
    <section className={styles.waiting}>
      <Typography.Title level={2}>AI 智能分析</Typography.Title>
      <Typography.Paragraph>
        视频下载并验证完成后，即可开始生成摘要、观点和思维导图。
      </Typography.Paragraph>
    </section>
  );
}

function metadata(duration: number, format?: MediaFormat): string {
  if (!format) return formatDuration(duration);
  return `${format.plan.height}p · ${format.plan.container_preference.toUpperCase()} · ${formatDuration(duration)}`;
}
