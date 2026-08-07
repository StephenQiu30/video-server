import type { ProColumns } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { Button, Image, Progress, Tag, Typography } from 'antd';

import stageCover from '@/assets/product-launch-stage.webp';
import type { DownloadHistoryItem, DownloadStatus } from '@/types/video';
import styles from './components.module.css';

export const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '排队中', value: 'queued' },
  { label: '下载中', value: 'running' },
  { label: '等待重试', value: 'retry_wait' },
  { label: '已完成', value: 'succeeded' },
  { label: '失败', value: 'failed' },
  { label: '已取消', value: 'cancelled' },
];

const statusLabels: Record<DownloadStatus, string> = {
  queued: '排队中',
  running: '下载中',
  retry_wait: '等待重试',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
};

export function historyColumns({
  downloadId,
  onDownload,
}: {
  downloadId: string | null;
  onDownload: (item: DownloadHistoryItem) => void;
}): ProColumns<DownloadHistoryItem>[] {
  return [
    {
      dataIndex: 'title',
      title: '视频',
      render: (_, item) => (
        <div className={styles.videoCell}>
          <Image
            alt={`${item.title} 视频封面`}
            fallback={stageCover}
            preview={false}
            src={item.thumbnail_url ?? stageCover}
          />
          <Typography.Text ellipsis strong>
            {item.title}
          </Typography.Text>
        </div>
      ),
    },
    { dataIndex: 'format_name', title: '清晰度 / 格式', width: 180 },
    {
      dataIndex: 'status',
      title: '状态',
      width: 180,
      render: (_, item) => <HistoryStatus item={item} />,
    },
    {
      dataIndex: 'created_at',
      title: '创建时间',
      valueType: 'dateTime',
      width: 190,
    },
    {
      fixed: 'right',
      title: '操作',
      valueType: 'option',
      width: 160,
      render: (_, item) => [
        <Button
          key="view"
          onClick={() => history.push(`/downloads/${item.id}`)}
          type="link"
        >
          查看任务
        </Button>,
        item.status === 'succeeded' ? (
          <Button
            key="download"
            loading={downloadId === item.id}
            onClick={() => onDownload(item)}
            type="link"
          >
            获取文件
          </Button>
        ) : null,
      ],
    },
  ];
}

function HistoryStatus({ item }: { item: DownloadHistoryItem }) {
  const active = ['queued', 'running', 'retry_wait'].includes(item.status);
  return (
    <div className={styles.statusCell}>
      <Tag color={active || item.status === 'succeeded' ? 'blue' : undefined}>
        {statusLabels[item.status]}
      </Tag>
      {active ? (
        <Progress percent={item.progress} showInfo={false} size="small" />
      ) : null}
    </div>
  );
}
