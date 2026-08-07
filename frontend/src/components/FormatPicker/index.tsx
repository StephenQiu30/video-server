import { Empty, Flex, Table, type TableColumnsType, Typography } from 'antd';

import type { MediaFormat } from '@/types/video';

type FormatPickerProps = {
  formats: MediaFormat[];
  selectedId: string;
  onChange: (id: string) => void;
};

const fpsLabels = {
  fps_30: '≤ 30 FPS',
  fps_60: '≤ 60 FPS',
  above_60: '> 60 FPS',
};

const columns: TableColumnsType<MediaFormat> = [
  {
    key: 'resolution',
    title: '清晰度',
    render: (_, { plan }) => (
      <Flex gap={2} vertical>
        <Typography.Text strong>{plan.height}P</Typography.Text>
        <Typography.Text type="secondary">
          {plan.width} × {plan.height} · {plan.dynamic_range.toUpperCase()}
        </Typography.Text>
      </Flex>
    ),
  },
  {
    dataIndex: 'display_name',
    key: 'format',
    title: '格式',
    render: (_, format) => (
      <Flex gap={2} vertical>
        <Typography.Text strong>
          {format.plan.container_preference.toUpperCase()}
        </Typography.Text>
        <Typography.Text type="secondary">
          {format.display_name}
        </Typography.Text>
      </Flex>
    ),
  },
  {
    key: 'video',
    title: '视频编码',
    render: (_, { plan }) => (
      <Flex gap={2} vertical>
        <Typography.Text strong>
          {plan.video_codec_family.toUpperCase()}
        </Typography.Text>
        <Typography.Text type="secondary">
          {fpsLabels[plan.fps_bucket]}
        </Typography.Text>
      </Flex>
    ),
  },
  {
    key: 'audio',
    title: '音频',
    render: (_, { plan }) => (
      <Flex gap={2} vertical>
        <Typography.Text strong>
          {plan.audio_codec_family.toUpperCase()}
        </Typography.Text>
        <Typography.Text type="secondary">
          {plan.audio_language ?? '默认音轨'}
        </Typography.Text>
      </Flex>
    ),
  },
];

export default function FormatPicker({
  formats,
  selectedId,
  onChange,
}: FormatPickerProps) {
  if (formats.length === 0) {
    return (
      <Empty
        description="没有可用的下载格式。"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
    <Table<MediaFormat>
      columns={columns}
      dataSource={formats}
      pagination={
        formats.length > 4
          ? { pageSize: 4, showSizeChanger: false, size: 'small' }
          : false
      }
      rowKey="id"
      rowSelection={{
        columnTitle: '选择',
        columnWidth: 64,
        getCheckboxProps: (format) => ({
          'aria-label': format.display_name,
        }),
        onChange: ([id]) => onChange(String(id)),
        selectedRowKeys: selectedId ? [selectedId] : [],
        type: 'radio',
      }}
      scroll={{ x: 640 }}
      size="middle"
    />
  );
}
