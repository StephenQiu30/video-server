import {
  CheckCircleOutlined,
  DownloadOutlined,
  PlayCircleOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { ProCard, ProDescriptions } from '@ant-design/pro-components';
import { Alert, Button, Flex, Image, Progress, Skeleton } from 'antd';

import stageCover from '@/assets/product-launch-stage.webp';
import type {
  AnalysisResult,
  DownloadJob,
  Inspection,
  MediaFormat,
} from '@/types/video';
import { formatDuration, formatMilliseconds } from '@/utils/format';

import styles from './MediaSidebar.module.css';

type MediaSidebarProps = {
  action: 'cancel' | 'download' | null;
  analysisResult: AnalysisResult | null;
  inspection: Inspection | null;
  job: DownloadJob;
  onCancel: () => void;
  onDownload: () => void;
};

const statusLabels = {
  queued: '等待处理',
  running: '下载中',
  retry_wait: '等待重试',
  succeeded: '下载已完成',
  failed: '下载失败',
  cancelled: '任务已取消',
};

export default function MediaSidebar({
  action,
  analysisResult,
  inspection,
  job,
  onCancel,
  onDownload,
}: MediaSidebarProps) {
  const format = inspection?.formats?.find((item) => item.id === job.format_id);
  const extension = format?.plan.container_preference ?? 'mp4';
  const title = inspection?.title ?? '视频下载任务';
  const isActive = ['queued', 'running', 'retry_wait'].includes(job.status);

  return (
    <ProCard
      className={styles.sidebar}
      styles={{ body: { padding: 14 } }}
      variant="outlined"
    >
      <div className={styles.cover}>
        <Image
          alt={`${title} 视频封面`}
          fallback={stageCover}
          placeholder
          preview={false}
          src={inspection?.thumbnail_url ?? stageCover}
        />
        <PlayCircleOutlined aria-hidden className={styles.play} />
        {inspection ? (
          <span className={styles.duration}>
            {formatDuration(inspection.duration_seconds)}
          </span>
        ) : null}
      </div>

      {!inspection ? <Skeleton active paragraph={{ rows: 4 }} /> : null}
      {inspection ? (
        <section className={styles.fileInfo}>
          <h2>文件信息</h2>
          <ProDescriptions<FileRecord>
            column={1}
            columns={fileColumns}
            dataSource={fileDetails(title, extension, format)}
            size="small"
          />
        </section>
      ) : null}

      <section className={styles.status}>
        <Flex align="center" gap={9}>
          {job.status === 'succeeded' ? (
            <SafetyCertificateOutlined />
          ) : (
            <CheckCircleOutlined />
          )}
          <strong>{statusLabels[job.status]}</strong>
        </Flex>
        <span>
          {job.status === 'succeeded'
            ? '文件完整性验证通过'
            : `任务进度 ${job.progress}%`}
        </span>
        {job.status !== 'succeeded' ? (
          <Progress percent={job.progress} showInfo={false} size="small" />
        ) : null}
      </section>

      {job.status === 'failed' ? (
        <Alert
          showIcon
          title={`错误代码：${job.error_code ?? 'unknown_error'}`}
          type="error"
        />
      ) : null}

      <Flex className={styles.actions} gap={10} vertical>
        {job.status === 'succeeded' ? (
          <Button
            aria-label="获取文件"
            icon={<DownloadOutlined />}
            loading={action === 'download'}
            onClick={onDownload}
            type="primary"
          >
            获取视频文件
          </Button>
        ) : null}
        {isActive ? (
          <Button
            aria-label="取消任务"
            danger
            loading={action === 'cancel'}
            onClick={onCancel}
          >
            取消任务
          </Button>
        ) : null}
        <Button href="/">返回新建下载</Button>
      </Flex>

      <section className={styles.chapters}>
        <h2>章节导航</h2>
        {analysisResult?.chapters.length ? (
          <ol>
            {analysisResult.chapters.map((chapter) => (
              <li key={`${chapter.start_ms}:${chapter.title}`}>
                <span>{formatMilliseconds(chapter.start_ms)}</span>
                <strong>{chapter.title}</strong>
              </li>
            ))}
          </ol>
        ) : (
          <p>AI 分析完成后将在这里显示章节。</p>
        )}
      </section>
    </ProCard>
  );
}

type FileRecord = {
  name: string;
  resolution: string;
  codec: string;
  container: string;
};

const fileColumns = [
  { title: '文件名', dataIndex: 'name', ellipsis: true },
  { title: '分辨率', dataIndex: 'resolution' },
  { title: '编码格式', dataIndex: 'codec' },
  { title: '容器格式', dataIndex: 'container' },
];

function fileDetails(
  title: string,
  extension: string,
  format?: MediaFormat,
): FileRecord {
  return {
    name: downloadFileName(title, extension),
    resolution: format ? `${format.plan.width} × ${format.plan.height}` : '—',
    codec: format ? codecLabel(format) : '—',
    container: extension.toUpperCase(),
  };
}

function downloadFileName(title: string, extension: string): string {
  const suffix = `.${extension}`;
  return title.toLowerCase().endsWith(suffix.toLowerCase())
    ? title
    : `${title}${suffix}`;
}

function codecLabel(format: MediaFormat): string {
  return `${format.plan.video_codec_family.toUpperCase()} + ${format.plan.audio_codec_family.toUpperCase()}`;
}
