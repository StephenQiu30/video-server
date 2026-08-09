import {
  CheckCircleOutlined,
  CloseOutlined,
  DownloadOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Descriptions,
  Flex,
  Progress,
  Space,
  Tag,
  Typography,
} from 'antd';

import type { DownloadJob, DownloadStatus, MediaFormat } from '@/types/video';
import './index.less';

type DownloadStateProps = {
  action: 'cancel' | 'download' | null;
  format?: MediaFormat;
  job: DownloadJob;
  onCancel: () => void;
  onDownload: () => void;
};

export default function DownloadState({
  action,
  format,
  job,
  onCancel,
  onDownload,
}: DownloadStateProps) {
  const active = ['queued', 'running', 'retry_wait'].includes(job.status);
  const complete = job.status === 'succeeded';
  return (
    <section className="download-state">
      <div className="download-state-head">
        <div>
          <p className="page-eyebrow">Download status</p>
          <Typography.Title
            className="status-title"
            level={2}
            style={{ marginTop: 4 }}
          >
            {statusLabels[job.status]}
          </Typography.Title>
        </div>
        <Tag color={statusColors[job.status]}>第 {job.attempt} 次尝试</Tag>
      </div>

      <Descriptions
        className="download-meta"
        column={3}
        items={[
          {
            key: 'format',
            label: '格式',
            children: format?.plan.container_preference.toUpperCase() ?? '—',
          },
          {
            key: 'resolution',
            label: '清晰度',
            children: format ? `${format.plan.height}P` : '—',
          },
          { key: 'stage', label: '阶段', children: displayStage(job) },
        ]}
        layout="vertical"
        size="small"
      />

      <div className="progress-labels">
        <span className="progress-number">{job.progress}%</span>
        <Typography.Text type="secondary">
          {statusLabels[job.status]}
        </Typography.Text>
      </div>
      <Progress
        percent={job.progress}
        showInfo={false}
        status={complete ? 'success' : 'active'}
      />

      {job.status === 'failed' ? (
        <Alert
          description={job.error_code ?? 'unknown_error'}
          title="下载失败"
          showIcon
          style={{ marginTop: 20 }}
          type="error"
        />
      ) : null}

      <Flex className="download-actions" gap={12} wrap>
        {complete ? (
          <Button
            icon={<DownloadOutlined aria-hidden />}
            loading={action === 'download'}
            onClick={onDownload}
            type="primary"
          >
            获取视频文件
          </Button>
        ) : null}
        {active ? (
          <Button
            icon={<CloseOutlined aria-hidden />}
            loading={action === 'cancel'}
            onClick={onCancel}
          >
            取消任务
          </Button>
        ) : null}
      </Flex>

      <Space className="status-footnote">
        {complete ? <SafetyCertificateOutlined /> : <CheckCircleOutlined />}
        {complete ? '文件完整性验证通过' : '任务由隔离的媒体 Runner 执行'}
      </Space>
    </section>
  );
}

const statusLabels: Record<DownloadStatus, string> = {
  queued: '等待处理',
  running: '正在下载',
  retry_wait: '等待重试',
  succeeded: '下载已完成',
  failed: '下载失败',
  cancelled: '任务已取消',
};

const statusColors: Record<DownloadStatus, string> = {
  queued: 'default',
  running: 'processing',
  retry_wait: 'warning',
  succeeded: 'success',
  failed: 'error',
  cancelled: 'default',
};

const stageLabels = {
  queued: '等待调度',
  revalidating: '重新验证',
  downloading: '下载媒体',
  remuxing: '封装媒体',
  verifying: '校验文件',
  uploading: '保存制品',
};

function displayStage(job: DownloadJob): string {
  if (job.status === 'succeeded') return '已完成';
  if (job.status === 'failed') return '已失败';
  if (job.status === 'cancelled') return '已取消';
  return job.stage ? stageLabels[job.stage] : '等待调度';
}