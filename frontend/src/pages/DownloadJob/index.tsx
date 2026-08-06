import { CheckCircleFilled } from '@ant-design/icons';
import {
  Alert,
  Breadcrumb,
  Button,
  Col,
  Flex,
  Grid,
  Row,
  Skeleton,
  Tag,
  Typography,
} from 'antd';
import { useCallback, useState } from 'react';

import AnalysisPanel from '@/features/analysis/AnalysisPanel';
import type { AnalysisJob } from '@/features/analysis/types';
import type { MediaFormat } from '@/features/download/types';
import { formatDuration } from '@/shared/format';
import BasicLayout from '@/shared/layout/BasicLayout';

import styles from './index.module.css';
import MediaSidebar from './MediaSidebar';
import { useDownloadJob } from './useDownloadJob';

type DownloadJobPageProps = {
  jobId: string;
  pollIntervalMs?: number;
};

export default function DownloadJobPage({
  jobId,
  pollIntervalMs = 1500,
}: DownloadJobPageProps) {
  const screens = Grid.useBreakpoint();
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
    <BasicLayout active="tasks">
      <main
        className={styles.page}
        style={{ padding: screens.sm ? '22px 24px 38px' : '18px 14px 30px' }}
      >
        <Breadcrumb items={[{ title: '任务' }, { title }]} />
        <Flex
          align={screens.sm ? 'center' : 'flex-start'}
          className={styles.heading}
          component="header"
          gap={14}
          vertical={!screens.sm}
          wrap
        >
          <Flex align="baseline" className={styles.titleRow} gap={12} wrap>
            <Typography.Title level={1}>{title}</Typography.Title>
            {state.inspection ? (
              <span>{metadata(state.inspection.duration_seconds, format)}</span>
            ) : null}
          </Flex>
          <Flex gap={8} wrap>
            {state.job?.status === 'succeeded' ? (
              <Tag color="success" icon={<CheckCircleFilled />}>
                文件已验证
              </Tag>
            ) : null}
            {analysisJob?.status === 'succeeded' ? (
              <Tag color="processing" icon={<CheckCircleFilled />}>
                分析已完成
              </Tag>
            ) : null}
          </Flex>
        </Flex>

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
            type="error"
          />
        ) : null}
        {state.inspectionError ? (
          <Alert
            className={styles.alert}
            showIcon
            title={state.inspectionError}
            type="warning"
          />
        ) : null}

        {state.loading && !state.job ? (
          <div className={styles.loading}>
            <Skeleton active paragraph={{ rows: 8 }} />
          </div>
        ) : null}

        {state.job ? (
          <Row align="top" gutter={[{ xs: 16, lg: 28 }, 20]}>
            <Col xs={24} lg={7} xl={6}>
              <MediaSidebar
                action={state.action}
                analysisResult={analysisJob?.result ?? null}
                inspection={state.inspection}
                job={state.job}
                onCancel={state.cancel}
                onDownload={state.download}
              />
            </Col>
            <Col xs={24} lg={17} xl={18}>
              {state.job.status === 'succeeded' ? (
                <AnalysisPanel
                  downloadId={state.job.id}
                  onJobChange={handleAnalysisJob}
                  pollIntervalMs={pollIntervalMs}
                />
              ) : (
                <WaitingForDownload />
              )}
            </Col>
          </Row>
        ) : null}
      </main>
    </BasicLayout>
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
