import Tag from 'antd/es/tag';
import Typography from 'antd/es/typography';
import styles from './analysis-panel.module.css';
import MindMapTree from './MindMapTree';
import type { AnalysisResult } from './types';

type AnalysisResultViewProps = {
  result: AnalysisResult;
};

export default function AnalysisResultView({
  result,
}: AnalysisResultViewProps) {
  return (
    <section aria-label="AI 分析结果" className={styles.result}>
      <header className={styles.resultHeader}>
        <Typography.Title level={3}>{result.title}</Typography.Title>
        <Tag>{result.language}</Tag>
      </header>

      <ResultSection title="摘要">
        <p className={styles.summaryText}>{result.summary.text}</p>
      </ResultSection>

      <ResultSection title="关键要点">
        <StatementList emptyText="暂无关键要点。" items={result.key_points} />
      </ResultSection>

      <ResultSection title="行动建议">
        <StatementList emptyText="暂无行动建议。" items={result.action_items} />
      </ResultSection>

      <ResultSection title="章节">
        {result.chapters.length > 0 ? (
          <ol className={styles.chapters}>
            {result.chapters.map((chapter) => (
              <li key={`${chapter.start_ms}:${chapter.title}`}>
                <div className={styles.chapterHeading}>
                  <strong>{chapter.title}</strong>
                  <span>
                    {formatTime(chapter.start_ms)}–{formatTime(chapter.end_ms)}
                  </span>
                </div>
                <p>{chapter.summary}</p>
              </li>
            ))}
          </ol>
        ) : (
          <p className={styles.empty}>暂无章节。</p>
        )}
      </ResultSection>

      <ResultSection title="思维导图">
        <MindMapTree root={result.mind_map} />
      </ResultSection>
    </section>
  );
}

function ResultSection({
  children,
  title,
}: {
  children: React.ReactNode;
  title: string;
}) {
  return (
    <section className={styles.resultSection}>
      <Typography.Title level={4}>{title}</Typography.Title>
      {children}
    </section>
  );
}

function StatementList({
  emptyText,
  items,
}: {
  emptyText: string;
  items: AnalysisResult['key_points'];
}) {
  return items.length > 0 ? (
    <ul className={styles.statements}>
      {items.map((item) => (
        <li key={`${item.text}:${item.evidence_segment_ids.join(',')}`}>
          {item.text}
        </li>
      ))}
    </ul>
  ) : (
    <p className={styles.empty}>{emptyText}</p>
  );
}

function formatTime(milliseconds: number): string {
  const totalSeconds = Math.floor(milliseconds / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = String(totalSeconds % 60).padStart(2, '0');
  const minuteText = hours > 0 ? String(minutes).padStart(2, '0') : minutes;
  return hours > 0
    ? `${hours}:${minuteText}:${seconds}`
    : `${minuteText}:${seconds}`;
}
