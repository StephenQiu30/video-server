import { DownloadOutlined, PlayCircleFilled } from '@ant-design/icons';
import { Button, Card, Image, Tag, Typography } from 'antd';

import stageCover from '@/assets/product-launch-stage.webp';
import FormatPicker from '@/components/FormatPicker';
import type { Inspection } from '@/types/video';
import { formatDuration } from '@/utils/format';

import styles from '../index.module.css';

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
    <Card
      className={styles.result}
      styles={{ body: { padding: 0 } }}
      variant="outlined"
    >
      <div className={styles.summary}>
        <div className={styles.media}>
          <Image
            alt={`${inspection.title} 视频封面`}
            fallback={stageCover}
            placeholder
            preview={false}
            src={inspection.thumbnail_url ?? stageCover}
          />
          <PlayCircleFilled aria-hidden className={styles.play} />
          <span>{formatDuration(inspection.duration_seconds)}</span>
        </div>
        <div className={styles.metadata}>
          <Typography.Title id="inspection-title" level={2}>
            {inspection.title}
          </Typography.Title>
          <Typography.Text type="secondary">
            <Tag bordered={false}>{inspection.extractor_key}</Tag>
            {formatDuration(inspection.duration_seconds)}
          </Typography.Text>
        </div>
      </div>

      <div className={styles.formats}>
        <FormatPicker
          formats={inspection.formats}
          onChange={onChange}
          selectedId={selectedId}
        />
        <Button
          aria-label="开始下载"
          className={styles.download}
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
    </Card>
  );
}
