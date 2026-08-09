import {
  ReloadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Flex,
  Progress,
  Select,
  Space,
  Tag,
  theme,
  Typography,
} from 'antd';
import { useEffect, useState } from 'react';

import AnalysisResultView from '@/components/AnalysisResultView';
import { useAnalysisJob } from '@/hooks/useAnalysisJob';
import type {
  AnalysisJob,
  AnalysisProfile,
  OutputLanguage,
} from '@/types/video';
import {
  cancellableAnalysisStatuses,
  stageLabels,
  statusLabels,
} from './status';
import './index.less';

type AnalysisPanelProps = {
  downloadId: string;
  onJobChange?: (job: AnalysisJob | null) => void;
  pollIntervalMs?: number;
};

export default function AnalysisPanel({
  downloadId,
  onJobChange,
  pollIntervalMs = 1500,
}: AnalysisPanelProps) {
  const state = useAnalysisJob(downloadId, pollIntervalMs);
  const [profile, setProfile] = useState<AnalysisProfile>('standard-v1');
  const [language, setLanguage] = useState<OutputLanguage>('zh-CN');
  const { action, error, job } = state;
  const { token } = theme.useToken();

  useEffect(() => onJobChange?.(job), [job, onJobChange]);

  if (job?.status === 'succeeded' && job.result) {
    return (
      <section className="analysis-card" aria-label="AI 智能分析">
        <div className="analysis-heading">
          <div>
            <p className="page-eyebrow">AI analysis</p>
            <Typography.Title level={2}>{job.result.title}</Typography.Title>
          </div>
          <Space wrap>
            <Tag color="success">分析已完成</Tag>
            <Button icon={<ReloadOutlined />} onClick={state.restart}>
              重新分析
            </Button>
          </Space>
        </div>
        <AnalysisResultView result={job.result} />
      </section>
    );
  }

  return (
    <section className="analysis-card" aria-labelledby="analysis-title">
      <div className="analysis-heading">
        <div>
          <p className="page-eyebrow">AI analysis</p>
          <Typography.Title id="analysis-title" level={2}>
            AI 智能分析
          </Typography.Title>
          <Typography.Text type="secondary">
            生成摘要、关键观点、章节和思维导图。
          </Typography.Text>
        </div>
        <RobotOutlined style={{ color: token.colorPrimary, fontSize: 26 }} />
      </div>

      {error ? (
        <Alert
          description={error}
          title="操作未完成"
          showIcon
          style={{ marginBlock: 24 }}
          type="error"
        />
      ) : null}

      {!job ? (
        <div className="analysis-form">
          <fieldset aria-label="分析模板" className="analysis-field">
            <Typography.Text strong>分析模板</Typography.Text>
            <div style={{ marginTop: 8 }}>
              <Select
                id="analysis-profile"
                onChange={(value) => setProfile(value as AnalysisProfile)}
                options={[{ label: '标准分析', value: 'standard-v1' }]}
                value={profile}
              />
            </div>
          </fieldset>
          <fieldset aria-label="输出语言" className="analysis-field">
            <Typography.Text strong>输出语言</Typography.Text>
            <div style={{ marginTop: 8 }}>
              <Select
                id="analysis:language"
                onChange={(value) => setLanguage(value as OutputLanguage)}
                options={[
                  { label: '简体中文', value: 'zh-CN' },
                  { label: 'English', value: 'en-US' },
                ]}
                value={language}
              />
            </div>
          </fieldset>
          <Button
            loading={action === 'start'}
            onClick={() => state.start({ profile, output_language: language })}
            type="primary"
          >
            开始 AI 分析
          </Button>
        </div>
      ) : (
        <AnalysisJobState job={job} state={state} />
      )}
    </section>
  );
}

function AnalysisJobState({
  job,
  state,
}: {
  job: AnalysisJob;
  state: ReturnType<typeof useAnalysisJob>;
}) {
  return (
    <div className="analysis-progress">
      <Flex align="center" justify="space-between">
        <Typography.Text strong>{statusLabels[job.status]}</Typography.Text>
        <Typography.Text code>{job.progress}%</Typography.Text>
      </Flex>
      <Progress percent={job.progress} showInfo={false} />
      <Typography.Paragraph type="secondary">
        当前阶段：{job.stage ? stageLabels[job.stage] : '等待调度'} · 第{' '}
        {job.attempt} 次尝试
      </Typography.Paragraph>
      <Space>
        {cancellableAnalysisStatuses.has(job.status) ? (
          <Button onClick={state.cancel}>取消分析</Button>
        ) : null}
        {job.status === 'failed' || job.status === 'cancelled' ? (
          <Button onClick={state.restart} type="primary">
            重新分析
          </Button>
        ) : null}
      </Space>

      <Typography.Text type="secondary">
        <SafetyCertificateOutlined style={{ marginInlineEnd: 4 }} />
        分析结果经证据校验，观点均来自视频转录内容。
      </Typography.Text>
    </div>
  );
}