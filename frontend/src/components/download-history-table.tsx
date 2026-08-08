'use client';

import { DownloadOutlined, EyeOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { Button, Tag } from 'antd';

import MediaCover from '@/components/media-cover';
import type {
  DownloadHistory,
  DownloadHistoryItem,
  DownloadStatus,
} from '@/types/video';

type DownloadHistoryTableProps = {
  data: DownloadHistory | null;
  loading: boolean;
  onDownload: (item: DownloadHistoryItem) => void;
  onOpen: (id: string) => void;
};

export default function DownloadHistoryTable({
  data,
  loading,
  onDownload,
  onOpen,
}: DownloadHistoryTableProps) {
  const columns: ProColumns<DownloadHistoryItem>[] = [
    {
      title: '视频',
      dataIndex: 'title',
      render: (_, item) => (
        <div className="history-video-cell">
          <MediaCover alt={`${item.title} 视频封面`} src={item.thumbnail_url} />
          <Button onClick={() => onOpen(item.id)} type="link">
            {item.title}
          </Button>
        </div>
      ),
    },
    { title: '格式', dataIndex: 'format_name', width: 150 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 150,
      render: (_, item) => (
        <Tag color={statusColors[item.status]}>
          {downloadStatusLabels[item.status]}
          {activeStatuses.has(item.status) ? ` · ${item.progress}%` : ''}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 190,
      renderText: (value: string) =>
        new Intl.DateTimeFormat('zh-CN', {
          dateStyle: 'medium',
          timeStyle: 'short',
        }).format(new Date(value)),
    },
    {
      title: '操作',
      valueType: 'option',
      width: 130,
      render: (_, item) =>
        item.status === 'succeeded' ? (
          <Button
            icon={<DownloadOutlined />}
            onClick={() => onDownload(item)}
            type="link"
          >
            获取文件
          </Button>
        ) : (
          <Button
            icon={<EyeOutlined />}
            onClick={() => onOpen(item.id)}
            type="link"
          >
            查看任务
          </Button>
        ),
    },
  ];

  return (
    <ProTable<DownloadHistoryItem>
      columns={columns}
      dataSource={data?.items ?? []}
      loading={loading}
      locale={{ emptyText: '没有匹配的下载记录' }}
      options={false}
      pagination={false}
      rowKey="id"
      search={false}
      toolBarRender={false}
    />
  );
}

export const downloadStatusLabels: Record<DownloadStatus, string> = {
  queued: '排队中',
  running: '下载中',
  retry_wait: '等待重试',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
};

const statusColors: Record<DownloadStatus, string> = {
  queued: 'default',
  running: 'processing',
  retry_wait: 'warning',
  succeeded: 'success',
  failed: 'error',
  cancelled: 'default',
};

const activeStatuses = new Set<DownloadStatus>([
  'queued',
  'running',
  'retry_wait',
]);
