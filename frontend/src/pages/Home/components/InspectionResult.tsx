import { DownloadOutlined } from '@ant-design/icons';
import { Button, Image, Tag, Typography } from 'antd';

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
  return (
    <div className={styles.workspace}>
      <section aria-labelledby="inspection-title" className={styles.summary}>
        <div className={styles.media}>
          <Image
            alt={`${inspection.title} 视频封面`}
            fallback={stageCover}
            placeholder
            preview={false}
            src={inspection.thumbnail_url ?? stageCover}
          />
          <span>{formatDuration(inspection.duration_seconds)}</span>
        </div>
        <div className={styles.metadata}>
          <Typography.Title id="inspection-title" level={2}>
            {inspection.title}
          </Typography.Title>
          <div className={styles.metaTags}>
            <Tag>{inspection.extractor_key}</Tag>
            <Tag>{formatDuration(inspection.duration_seconds)}</Tag>
            <Tag>{inspection.formats.length} 个格式</Tag>
          </div>
          <dl className={styles.details}>
            <div>
              <dt>媒体 ID</dt>
              <dd>{inspection.provider_media_id}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section aria-labelledby="format-title" className={styles.formats}>
        <header className={styles.formatHeading}>
          <Typography.Title id="format-title" level={2}>
            选择下载格式
          </Typography.Title>
          <Typography.Text type="secondary">
            选择适合你的清晰度和文件格式
          </Typography.Text>
        </header>
        <FormatPicker
          formats={inspection.formats}
          onChange={onChange}
          selectedId={selectedId}
        />
        <div className={styles.downloadBar}>
          <Typography.Text type="secondary">
            创建后可在任务页查看进度
          </Typography.Text>
          <Button
            aria-label="开始下载"
            disabled={!selectedId}
            icon={<DownloadOutlined />}
            loading={busy}
            onClick={onCreate}
            size="large"
            type="primary"
          >
            开始下载
          </Button>
        </div>
      </section>
    </div>
  );
}
