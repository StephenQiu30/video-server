import Alert from 'antd/es/alert';
import Button from 'antd/es/button';
import Card from 'antd/es/card';
import Progress from 'antd/es/progress';
import Space from 'antd/es/space';
import Tag from 'antd/es/tag';
import Typography from 'antd/es/typography';
import { type FormEvent, useState } from 'react';

import AnalysisResultView from './AnalysisResultView';
import styles from './analysis-panel.module.css';
import type {
  AnalysisProfile,
  AnalysisStage,
  AnalysisStatus,
  OutputLanguage,
} from './types';
import { useAnalysisJob } from './useAnalysisJob';

const statusLabels: Record<AnalysisStatus, string> = {
  queued: '等待分析',
  running: '分析中',
  retry_wait: '等待重试',
  succeeded: '分析已完成',
  failed: '分析失败',
  cancelled: '分析已取消',
};

const stageLabels: Record<AnalysisStage, string> = {
  preparing: '准备视频',
  transcribing: '转写音频',
  analyzing: '理解内容',
  validating: '校验结果',
};

const cancellable = new Set<AnalysisStatus>([
  'queued',
  'running',
  'retry_wait',
]);

type AnalysisPanelProps = {
  downloadId: string;
  pollIntervalMs?: number;
};

export default function AnalysisPanel({
  downloadId,
  pollIntervalMs = 1500,
}: AnalysisPanelProps) {
  const [profile, setProfile] = useState<AnalysisProfile>('standard-v1');
  const [outputLanguage, setOutputLanguage] = useState<OutputLanguage>('zh-CN');
  const state = useAnalysisJob(downloadId, pollIntervalMs);
  const { action, error, job } = state;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void state.start({ profile, output_language: outputLanguage });
  }

  return (
    <Card className={styles.panel} variant="borderless">
      <header className={styles.panelHeader}>
        <div>
          <Typography.Title level={2}>AI 智能分析</Typography.Title>
          <Typography.Paragraph type="secondary">
            下载完成后生成摘要、要点、行动建议、章节与思维导图。
          </Typography.Paragraph>
        </div>
        <Tag color="geekblue">结构化结果</Tag>
      </header>

      {error ? (
        <Alert
          action={
            job && cancellable.has(job.status) ? (
              <Button onClick={state.retryPoll} size="small">
                重试查询
              </Button>
            ) : undefined
          }
          className={styles.alert}
          showIcon
          title={error}
          type="error"
        />
      ) : null}

      {!job ? (
        <form className={styles.form} onSubmit={handleSubmit}>
          <label>
            <span>分析模板</span>
            <select
              onChange={(event) =>
                setProfile(event.target.value as AnalysisProfile)
              }
              value={profile}
            >
              <option value="standard-v1">标准分析</option>
            </select>
          </label>
          <label>
            <span>输出语言</span>
            <select
              onChange={(event) =>
                setOutputLanguage(event.target.value as OutputLanguage)
              }
              value={outputLanguage}
            >
              <option value="zh-CN">简体中文</option>
              <option value="en-US">English</option>
            </select>
          </label>
          <Button
            aria-label="开始 AI 分析"
            htmlType="submit"
            loading={action === 'start'}
            size="large"
            type="primary"
          >
            开始 AI 分析
          </Button>
        </form>
      ) : (
        <section aria-live="polite" className={styles.job}>
          <div className={styles.jobHeading}>
            <div>
              <span className={styles.label}>分析状态</span>
              <Typography.Title level={3}>
                {statusLabels[job.status]}
              </Typography.Title>
            </div>
            <Tag color={job.status === 'succeeded' ? 'green' : 'blue'}>
              第 {job.attempt} 次尝试
            </Tag>
          </div>

          <Progress
            percent={job.progress}
            status={progressStatus(job.status)}
          />
          <div className={styles.jobMeta}>
            <span>当前阶段：{job.stage ? stageLabels[job.stage] : '—'}</span>
            <span>输出语言：{job.output_language}</span>
          </div>

          {job.status === 'failed' ? (
            <Alert
              showIcon
              title={`错误代码：${job.error_code ?? 'unknown_error'}`}
              type="error"
            />
          ) : null}

          <Space wrap>
            {cancellable.has(job.status) ? (
              <Button
                aria-label="取消分析"
                danger
                loading={action === 'cancel'}
                onClick={state.cancel}
              >
                取消分析
              </Button>
            ) : null}
            {job.status === 'failed' || job.status === 'cancelled' ? (
              <Button onClick={state.restart}>重新分析</Button>
            ) : null}
          </Space>

          {job.status === 'succeeded' && job.result ? (
            <AnalysisResultView result={job.result} />
          ) : null}
          {job.status === 'succeeded' && !job.result ? (
            <Alert showIcon title="分析结果暂不可用" type="warning" />
          ) : null}
        </section>
      )}
    </Card>
  );
}

function progressStatus(
  status: AnalysisStatus,
): 'active' | 'exception' | 'success' {
  if (status === 'failed') {
    return 'exception';
  }
  return status === 'succeeded' ? 'success' : 'active';
}
