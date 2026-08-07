import { DownloadOutlined } from '@ant-design/icons';
import { Button, Descriptions, Image, Space, Tag, Typography } from 'antd';

import stageCover from '@/assets/product-launch-stage.webp';
import FormatPicker from '@/components/FormatPicker';
import type { Inspection } from '@/types/video';
import { formatDuration } from '@/utils/format';

import styles from './InspectionResult.module.css';

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
    <div className={styles.workspace}>
      <section aria-labelledby="inspection-title" className={styles.summary}>
        <Typography.Title className={styles.sectionTitle} level={2}>
          视频信息
        </Typography.Title>
        <div className={styles.overview}>
          <div
            className={styles.media}
            style={{ backgroundImage: `url(${stageCover})` }}
          >
            <Image
              alt={`${inspection.title} 视频封面`}
              fallback={stageCover}
              preview={false}
              src={inspection.thumbnail_url ?? stageCover}
            />
            <span>{formatDuration(inspection.duration_seconds)}</span>
          </div>
          <div className={styles.metadata}>
            <Typography.Title id="inspection-title" level={3}>
              {inspection.title}
            </Typography.Title>
            <Space size={6} wrap>
              <Tag color="blue">{inspection.extractor_key}</Tag>
              <Tag>{inspection.formats.length} 个格式</Tag>
            </Space>
          </div>
        </div>
        <Descriptions
          className={styles.details}
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
        />
      </section>

      <section aria-labelledby="format-title" className={styles.formats}>
        <Typography.Title
          className={styles.sectionTitle}
          id="format-title"
          level={2}
        >
          选择下载格式
        </Typography.Title>
        <FormatPicker
          formats={inspection.formats}
          onChange={onChange}
          selectedId={selectedId}
        />
        <div className={styles.downloadBar}>
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
            size="large"
            type="primary"
          >
            创建下载任务
          </Button>
        </div>
      </section>
    </div>
  );
}
