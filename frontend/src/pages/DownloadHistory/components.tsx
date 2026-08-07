import { ClockCircleOutlined, DownloadOutlined } from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import {
  Button,
  Flex,
  Image,
  Progress,
  Skeleton,
  Space,
  Statistic,
  Tag,
  Typography,
} from 'antd';

import stageCover from '@/assets/product-launch-stage.webp';
import type { DownloadHistoryItem, DownloadStatus } from '@/types/video';
import styles from './components.module.css';

const statusLabels: Record<DownloadStatus, string> = {
  queued: '排队中',
  running: '下载中',
  retry_wait: '等待重试',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
};

const statusColors: Record<DownloadStatus, string> = {
  queued: 'blue',
  running: 'processing',
  retry_wait: 'gold',
  succeeded: 'success',
  failed: 'error',
  cancelled: 'default',
};

export function StatCard({
  label,
  tone,
  value,
}: {
  label: string;
  tone?: 'success' | 'active' | 'error';
  value: number;
}) {
  return (
    <ProCard
      className={`${styles.statCard} ${tone ? styles[tone] : ''}`}
      variant="outlined"
    >
      <Statistic title={label} value={value} />
    </ProCard>
  );
}

export function HistoryItem({
  item,
  loading,
  onDownload,
}: {
  item: DownloadHistoryItem;
  loading: boolean;
  onDownload: (item: DownloadHistoryItem) => void;
}) {
  const active = ['queued', 'running', 'retry_wait'].includes(item.status);
  return (
    <article className={styles.record}>
      <Image
        alt={`${item.title} 视频封面`}
        className={styles.cover}
        fallback={stageCover}
        preview={false}
        src={item.thumbnail_url ?? stageCover}
      />
      <div className={styles.recordBody}>
        <Flex align="center" gap={8} wrap>
          <Typography.Title
            className={styles.recordTitle}
            ellipsis={{ rows: 1 }}
            level={3}
          >
            {item.title}
          </Typography.Title>
          <Tag color={statusColors[item.status]}>
            {statusLabels[item.status]}
          </Tag>
        </Flex>
        <Typography.Text className={styles.format} type="secondary">
          {item.format_name}
        </Typography.Text>
        <Typography.Text className={styles.time} type="secondary">
          <ClockCircleOutlined /> {formatDate(item.created_at)}
        </Typography.Text>
        {active ? (
          <Progress percent={item.progress} showInfo={false} size="small" />
        ) : null}
        {item.status === 'failed' ? (
          <Typography.Text className={styles.errorCode} type="danger">
            错误代码：{item.error_code ?? 'unknown_error'}
          </Typography.Text>
        ) : null}
      </div>
      <Space className={styles.actions} orientation="vertical" size={8}>
        <Button onClick={() => history.push(`/downloads/${item.id}`)}>
          查看任务
        </Button>
        {item.status === 'succeeded' ? (
          <Button
            icon={<DownloadOutlined />}
            loading={loading}
            onClick={() => onDownload(item)}
            type="primary"
          >
            获取文件
          </Button>
        ) : null}
      </Space>
    </article>
  );
}

export function HistorySkeleton() {
  return (
    <div className={styles.skeleton}>
      {[1, 2, 3].map((item) => (
        <Skeleton
          active
          avatar={{ shape: 'square', size: 112 }}
          key={item}
          paragraph={{ rows: 2 }}
        />
      ))}
    </div>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    month: '2-digit',
  }).format(new Date(value));
}
