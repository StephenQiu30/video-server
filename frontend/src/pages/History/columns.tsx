import { DownloadOutlined, EyeOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Tag } from 'antd';

import MediaCover from '@/components/MediaCover';
import type { DownloadHistoryItem, DownloadStatus } from '@/types/video';

type HistoryColumnActions = {
  onDownload: (item: DownloadHistoryItem) => void;
  onOpen: (id: string) => void;
};

export function createHistoryColumns({
  onDownload,
  onOpen,
}: HistoryColumnActions): ProColumns<DownloadHistoryItem>[] {
  return [
    {
      title: '视频标题',
      dataIndex: 'search',
      valueType: 'text',
      hideInTable: true,
      order: 2,
      fieldProps: {
        allowClear: true,
        maxLength: 128,
        placeholder: '按视频标题搜索',
      },
    },
    {
      title: '视频',
      dataIndex: 'title',
      search: false,
      render: (_, item) => (
        <div className="history-video-cell">
          <MediaCover
            alt={`${item.title} 视频封面`}
            className="history-cover"
            src={item.thumbnail_url}
          />
          <Button onClick={() => onOpen(item.id)} type="link">
            {item.title}
          </Button>
        </div>
      ),
    },
    {
      title: '格式',
      dataIndex: 'format_name',
      search: false,
      width: 150,
    },
    {
      title: '状态',
      dataIndex: 'status',
      valueType: 'select',
      valueEnum: statusValueEnum,
      order: 1,
      width: 160,
      fieldProps: {
        allowClear: true,
        placeholder: '全部状态',
      },
      render: (_, item) => (
        <Tag color={statusColors[item.status]}>
          {statusLabels[item.status]}
          {activeStatuses.has(item.status) ? ` · ${item.progress}%` : ''}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      valueType: 'dateTime',
      search: false,
      width: 190,
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
}

const statusLabels: Record<DownloadStatus, string> = {
  queued: '排队中',
  running: '下载中',
  retry_wait: '等待重试',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
};

const statusValueEnum = Object.fromEntries(
  Object.entries(statusLabels).map(([value, label]) => [
    value,
    { text: label },
  ]),
);

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
