import {
  BulbOutlined,
  CheckCircleFilled,
  DownloadOutlined,
  FileTextOutlined,
  NodeIndexOutlined,
  PlayCircleFilled,
} from '@ant-design/icons';
import { Button, Card, Image, Tabs, Tag, Typography } from 'antd';
import type { ReactNode } from 'react';

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

const analysisItems = [
  {
    key: 'summary',
    label: '摘要',
    children: (
      <AnalysisPreview
        icon={<FileTextOutlined />}
        text="AI 将根据视频内容生成结构化摘要，帮助你快速掌握核心信息。"
      />
    ),
  },
  {
    key: 'points',
    label: '关键观点',
    children: (
      <AnalysisPreview
        icon={<BulbOutlined />}
        text="分析完成后将提炼视频中的关键观点，并保留可追溯的内容证据。"
      />
    ),
  },
  {
    key: 'actions',
    label: '行动项',
    children: (
      <AnalysisPreview
        icon={<CheckCircleFilled />}
        text="从视频中识别可执行的行动建议，便于后续整理与跟进。"
      />
    ),
  },
  {
    key: 'mind-map',
    label: '思维导图',
    children: (
      <AnalysisPreview
        icon={<NodeIndexOutlined />}
        text="用思维导图呈现内容结构与逻辑关系，下载并验证后即可生成。"
      />
    ),
  },
];

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
            <PlayCircleFilled aria-hidden className={styles.play} />
            <span>{formatDuration(inspection.duration_seconds)}</span>
          </div>
          <div className={styles.metadata}>
            <Typography.Title id="inspection-title" level={2}>
              {inspection.title}
            </Typography.Title>
            <div className={styles.metaTags}>
              <Tag color="blue">{inspection.extractor_key}</Tag>
              <Tag>{formatDuration(inspection.duration_seconds)}</Tag>
              <Tag>{inspection.formats.length} 个可用格式</Tag>
            </div>
            <dl className={styles.details}>
              <div>
                <dt>平台</dt>
                <dd>{inspection.extractor_key}</dd>
              </div>
              <div>
                <dt>媒体 ID</dt>
                <dd>{inspection.provider_media_id}</dd>
              </div>
            </dl>
          </div>
        </section>

        <section aria-labelledby="format-title" className={styles.formats}>
          <header className={styles.formatHeading}>
            <div>
              <Typography.Title id="format-title" level={2}>
                选择下载格式
              </Typography.Title>
              <Typography.Text type="secondary">
                选择适合你的格式与清晰度
              </Typography.Text>
            </div>
          </header>
          <FormatPicker
            formats={inspection.formats}
            onChange={onChange}
            selectedId={selectedId}
          />
          <div className={styles.downloadBar}>
            <Typography.Text type="secondary">
              文件将在服务端下载并完成完整性验证
            </Typography.Text>
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
        </section>
      </div>

      <section
        aria-labelledby="analysis-preview-title"
        className={styles.analysisPreview}
      >
        <div className={styles.analysisHeading}>
          <Typography.Title id="analysis-preview-title" level={2}>
            AI 智能分析预览
          </Typography.Title>
          <Typography.Text type="secondary">
            下载完成并验证通过后可用
          </Typography.Text>
        </div>
        <Tabs defaultActiveKey="summary" items={analysisItems} />
      </section>
    </Card>
  );
}

function AnalysisPreview({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <div className={styles.previewContent}>
      <span className={styles.previewIcon}>{icon}</span>
      <p>{text}</p>
      <ul>
        <li>
          <CheckCircleFilled /> 自动提炼核心内容
        </li>
        <li>
          <CheckCircleFilled /> 生成结构化分析结果
        </li>
        <li>
          <CheckCircleFilled /> 在任务页集中查看
        </li>
      </ul>
    </div>
  );
}
