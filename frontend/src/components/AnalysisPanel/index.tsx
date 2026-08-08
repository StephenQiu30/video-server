'use client';

import { ReloadOutlined, RobotOutlined } from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import {
  Alert,
  Button,
  Flex,
  Progress,
  Select,
  Space,
  Tag,
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

  useEffect(() => onJobChange?.(job), [job, onJobChange]);

  if (job?.status === 'succeeded' && job.result) {
    return (
      <ProCard className="analysis-card">
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
      </ProCard>
    );
  }

  return (
    <ProCard className="analysis-card">
      <div className="analysis-heading">
        <div>
          <p className="page-eyebrow">AI analysis</p>
          <Typography.Title level={2}>AI 智能分析</Typography.Title>
          <Typography.Text type="secondary">
            生成摘要、关键观点、章节和思维导图。
          </Typography.Text>
        </div>
        <RobotOutlined style={{ color: '#1677ff', fontSize: 26 }} />
      </div>

      {error ? (
        <Alert
          description={error}
          message="操作未完成"
          showIcon
          style={{ marginBlock: 24 }}
          type="error"
        />
      ) : null}

      {!job ? (
        <div className="analysis-form">
          <Field label="分析模板">
            <Select
              id="analysis-profile"
              onChange={(value) => setProfile(value)}
              options={[{ label: '标准分析', value: 'standard-v1' }]}
              value={profile}
            />
          </Field>
          <Field label="输出语言">
            <Select
              id="analysis-language"
              onChange={(value) => setLanguage(value)}
              options={[
                { label: '简体中文', value: 'zh-CN' },
                { label: 'English', value: 'en-US' },
              ]}
              value={language}
            />
          </Field>
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
    </ProCard>
  );
}

function Field({
  children,
  label,
}: {
  children: React.ReactNode;
  label: string;
}) {
  return (
    <fieldset aria-label={label} className="analysis-field">
      <Typography.Text strong>{label}</Typography.Text>
      <div style={{ marginTop: 8 }}>{children}</div>
    </fieldset>
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
    </div>
  );
}
