import { CopyOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { Button, Col, Flex, Grid, Row, Tabs, Typography } from 'antd';

import { formatMilliseconds } from '@/shared/format';

import styles from './analysis-result.module.css';
import MindMapTree from './MindMapTree';
import type { AnalysisResult, EvidenceStatement } from './types';

type AnalysisResultViewProps = {
  result: AnalysisResult;
};

export default function AnalysisResultView({
  result,
}: AnalysisResultViewProps) {
  const screens = Grid.useBreakpoint();
  const items = [
    {
      key: 'summary',
      label: '摘要',
      children: <Summary result={result} screens={screens} />,
    },
    {
      key: 'points',
      label: '关键观点',
      children: (
        <StatementSection
          emptyText="暂无关键观点。"
          items={result.key_points}
          screens={screens}
          title="关键要点"
        />
      ),
    },
    {
      key: 'actions',
      label: '行动项',
      children: (
        <StatementSection
          emptyText="暂无行动建议。"
          items={result.action_items}
          screens={screens}
          title="行动建议"
        />
      ),
    },
    {
      key: 'mind-map',
      label: '思维导图',
      children: (
        <section>
          <Typography.Title level={3}>思维导图</Typography.Title>
          <MindMapTree root={result.mind_map} />
        </section>
      ),
    },
  ];

  return (
    <section aria-label="AI 分析结果" className={styles.result}>
      <Tabs
        defaultActiveKey="summary"
        items={items}
        size={screens.sm ? 'middle' : 'small'}
        tabBarGutter={screens.sm ? 32 : 16}
      />
    </section>
  );
}

function Summary({
  result,
  screens,
}: {
  result: AnalysisResult;
  screens: ReturnType<typeof Grid.useBreakpoint>;
}) {
  return (
    <div className={styles.summaryTab}>
      <section className={styles.summaryBlock}>
        <Typography.Title level={3}>摘要</Typography.Title>
        <p>{result.summary.text}</p>
        <span>
          <InfoCircleOutlined /> 所有观点均来自本次视频转录证据
        </span>
      </section>

      <StatementSection
        compact
        emptyText="暂无关键观点。"
        items={result.key_points}
        screens={screens}
        title="关键要点"
      />

      <Row gutter={[{ xs: 0, lg: 28 }, 22]}>
        <Col xs={24} lg={9}>
          <section>
            <Typography.Title level={3}>章节</Typography.Title>
            {result.chapters.length ? (
              <ol className={styles.timeline}>
                {result.chapters.map((chapter) => (
                  <li key={`${chapter.start_ms}:${chapter.title}`}>
                    <span>{formatMilliseconds(chapter.start_ms)}</span>
                    <div>
                      <strong>{chapter.title}</strong>
                      <p>{chapter.summary}</p>
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <p className={styles.empty}>暂无章节。</p>
            )}
          </section>
        </Col>
        <Col xs={24} lg={15}>
          <section
            style={
              screens.lg
                ? { borderLeft: '1px solid #e5e7eb', paddingLeft: 28 }
                : { borderTop: '1px solid #e5e7eb', paddingTop: 22 }
            }
          >
            <Typography.Title level={3}>思维导图预览</Typography.Title>
            <MindMapTree root={result.mind_map} />
          </section>
        </Col>
      </Row>
    </div>
  );
}

function StatementSection({
  compact = false,
  emptyText,
  items,
  screens,
  title,
}: {
  compact?: boolean;
  emptyText: string;
  items: EvidenceStatement[];
  screens: ReturnType<typeof Grid.useBreakpoint>;
  title: string;
}) {
  return (
    <section className={compact ? styles.compactSection : undefined}>
      <Typography.Title level={3}>{title}</Typography.Title>
      {items.length ? (
        <ul className={styles.statements}>
          {items.map((item, index) => (
            <Flex
              align="center"
              component="li"
              gap={screens.sm ? 12 : 8}
              key={`${item.text}:${item.evidence_segment_ids.join(',')}`}
            >
              <span style={{ width: screens.sm ? 50 : 24 }}>
                {compact ? `0${index + 1}` : '•'}
              </span>
              <p style={{ flex: 1 }}>{item.text}</p>
              <Button
                aria-label={`复制观点 ${index + 1}`}
                icon={<CopyOutlined />}
                onClick={() => void navigator.clipboard?.writeText(item.text)}
                size="small"
                type="text"
              />
            </Flex>
          ))}
        </ul>
      ) : (
        <p className={styles.empty}>{emptyText}</p>
      )}
    </section>
  );
}
