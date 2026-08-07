import { DownloadOutlined } from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import {
  Button,
  Col,
  Descriptions,
  Flex,
  Row,
  Space,
  Tag,
  Typography,
} from 'antd';

import FormatPicker from '@/components/FormatPicker';
import type { Inspection } from '@/types/video';
import { formatDuration } from '@/utils/format';

type InspectionResultProps = {
  busy: boolean;
  inspection: Inspection;
  onChange: (id: string) => void;
  onCreate: () => void;
  selectedId: string;
};

export default function InspectionResult({
  busy,
  inspection,
  onChange,
  onCreate,
  selectedId,
}: InspectionResultProps) {
  const selected = inspection.formats.find(({ id }) => id === selectedId);

  return (
    <Row gutter={[16, 16]}>
      <Col lg={10} xs={24}>
        <ProCard title="视频信息" variant="outlined">
          <Flex gap={12} vertical>
            <Typography.Title id="inspection-title" level={5}>
              {inspection.title}
            </Typography.Title>
            <Space size={6} wrap>
              <Tag color="blue">{inspection.extractor_key}</Tag>
              <Tag>{inspection.formats.length} 个格式</Tag>
            </Space>
          </Flex>
          <Descriptions
            column={1}
            items={[
              {
                key: 'id',
                label: '视频 ID',
                children: inspection.provider_media_id,
              },
              {
                key: 'duration',
                label: '视频时长',
                children: formatDuration(inspection.duration_seconds),
              },
              {
                key: 'source',
                label: '来源平台',
                children: inspection.extractor_key,
              },
            ]}
            size="small"
            style={{ marginTop: 20 }}
          />
        </ProCard>
      </Col>
      <Col lg={14} xs={24}>
        <ProCard title="选择下载格式" variant="outlined">
          <FormatPicker
            formats={inspection.formats}
            onChange={onChange}
            selectedId={selectedId}
          />
          <Flex align="center" gap={16} justify="space-between" wrap>
            <Typography.Text>
              {selected
                ? `已选择：${selected.plan.height}P · ${selected.plan.container_preference.toUpperCase()}`
                : '请选择下载格式'}
            </Typography.Text>
            <Button
              aria-label="创建下载任务"
              disabled={!selectedId}
              icon={<DownloadOutlined />}
              loading={busy}
              onClick={onCreate}
              type="primary"
            >
              创建下载任务
            </Button>
          </Flex>
        </ProCard>
      </Col>
    </Row>
  );
}
