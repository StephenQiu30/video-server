'use client';

import {
  CheckOutlined,
  CopyOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { Button, List, Tabs, Typography } from 'antd';
import { useState } from 'react';

import MindMapTree from '@/components/MindMapTree';
import type { AnalysisResult, EvidenceStatement } from '@/types/video';
import { formatMilliseconds } from '@/utils/format';

export default function AnalysisResultView({
  result,
}: {
  result: AnalysisResult;
}) {
  return (
    <section aria-label="AI 分析结果" className="analysis-tabs">
      <Tabs
        defaultActiveKey="summary"
        items={[
          {
            key: 'summary',
            label: '摘要',
            children: (
              <>
                <section className="result-section">
                  <Typography.Title level={3}>摘要</Typography.Title>
                  <Typography.Paragraph>
                    {result.summary.text}
                  </Typography.Paragraph>
                  <Typography.Text type="secondary">
                    <InfoCircleOutlined /> 所有观点均来自本次视频转录证据
                  </Typography.Text>
                </section>
                <Statements items={result.key_points} title="关键要点" />
                <div className="result-grid">
                  <Chapters result={result} />
                  <section>
                    <Typography.Title level={3}>思维导图预览</Typography.Title>
                    <MindMapTree root={result.mind_map} />
                  </section>
                </div>
              </>
            ),
          },
          {
            key: 'points',
            label: '关键观点',
            children: <Statements items={result.key_points} title="关键观点" />,
          },
          {
            key: 'actions',
            label: '行动项',
            children: (
              <Statements items={result.action_items} title="行动建议" />
            ),
          },
          {
            key: 'mind-map',
            label: '思维导图',
            children: <MindMapTree root={result.mind_map} />,
          },
        ]}
      />
    </section>
  );
}

function Statements({
  items,
  title,
}: {
  items: EvidenceStatement[];
  title: string;
}) {
  return (
    <section className="result-section">
      <Typography.Title level={3}>{title}</Typography.Title>
      <List
        dataSource={items}
        locale={{ emptyText: '暂无内容。' }}
        renderItem={(item, index) => (
          <List.Item>
            <Statement index={index} item={item} />
          </List.Item>
        )}
      />
    </section>
  );
}

function Statement({
  item,
  index,
}: {
  item: EvidenceStatement;
  index: number;
}) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    await navigator.clipboard?.writeText(item.text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }
  return (
    <div className="statement-row">
      <Typography.Text code>
        {String(index + 1).padStart(2, '0')}
      </Typography.Text>
      <Typography.Text>{item.text}</Typography.Text>
      <Button
        aria-label={`复制观点 ${index + 1}`}
        icon={copied ? <CheckOutlined /> : <CopyOutlined />}
        onClick={() => void copy()}
        type="text"
      />
    </div>
  );
}

function Chapters({ result }: { result: AnalysisResult }) {
  return (
    <section>
      <Typography.Title level={3}>章节</Typography.Title>
      <List
        dataSource={result.chapters}
        renderItem={(chapter) => (
          <List.Item>
            <div className="chapter-row">
              <span className="chapter-time">
                {formatMilliseconds(chapter.start_ms)}
              </span>
              <span>
                <Typography.Text strong>{chapter.title}</Typography.Text>
                <Typography.Paragraph type="secondary">
                  {chapter.summary}
                </Typography.Paragraph>
              </span>
            </div>
          </List.Item>
        )}
      />
    </section>
  );
}
