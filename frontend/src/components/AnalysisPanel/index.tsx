import { ReloadOutlined } from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import {
  Alert,
  Button,
  Col,
  Flex,
  Form,
  Grid,
  Progress,
  Row,
  Select,
  Space,
  Tag,
  Typography,
} from 'antd';
import { useEffect } from 'react';

import AnalysisResultView from '@/components/AnalysisResultView';
import { useAnalysisJob } from '@/hooks/useAnalysisJob';
import type { AnalysisJob, CreateAnalysisInput } from '@/types/video';

import styles from './index.module.css';
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
  const screens = Grid.useBreakpoint();
  const state = useAnalysisJob(downloadId, pollIntervalMs);
  const { action, error, job } = state;

  useEffect(() => onJobChange?.(job), [job, onJobChange]);

  return (
    <ProCard
      className={styles.panel}
      styles={{ body: { padding: 0 } }}
      variant="outlined"
    >
      {error ? (
        <Alert
          action={
            job && cancellableAnalysisStatuses.has(job.status) ? (
              <Button onClick={state.retryPoll}>重试查询</Button>
            ) : undefined
          }
          className={styles.alert}
          showIcon
          title={error}
          type="error"
        />
      ) : null}

      {!job ? (
        <section
          className={styles.setup}
          style={{ padding: screens.sm ? 28 : 20 }}
        >
          <Flex
            align={screens.sm ? 'flex-start' : 'stretch'}
            gap={16}
            justify="space-between"
            vertical={!screens.sm}
          >
            <div className={styles.setupHeading}>
              <Typography.Title level={2}>AI 智能分析</Typography.Title>
              <Typography.Paragraph type="secondary">
                下载完成后生成摘要、观点、行动项、章节与思维导图。
              </Typography.Paragraph>
            </div>
            <Tag color="blue">结构化结果</Tag>
          </Flex>
          <Form<CreateAnalysisInput>
            className={styles.form}
            initialValues={{ profile: 'standard-v1', output_language: 'zh-CN' }}
            layout="vertical"
            onFinish={(values) => void state.start(values)}
          >
            <Row align="bottom" gutter={[16, 0]}>
              <Col xs={24} sm={9}>
                <Form.Item label="分析模板" name="profile">
                  <Select
                    options={[{ label: '标准分析', value: 'standard-v1' }]}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={9}>
                <Form.Item label="输出语言" name="output_language">
                  <Select
                    options={[
                      { label: '简体中文', value: 'zh-CN' },
                      { label: 'English', value: 'en-US' },
                    ]}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={6}>
                <Form.Item>
                  <Button
                    aria-label="开始 AI 分析"
                    block
                    htmlType="submit"
                    loading={action === 'start'}
                    type="primary"
                  >
                    开始 AI 分析
                  </Button>
                </Form.Item>
              </Col>
            </Row>
          </Form>
        </section>
      ) : job.status === 'succeeded' && job.result ? (
        <>
          <Flex
            align={screens.sm ? 'center' : 'flex-start'}
            className={styles.resultToolbar}
            gap={12}
            justify="space-between"
            vertical={!screens.sm}
          >
            <strong>{job.result.title}</strong>
            <Flex align="center" gap={12} wrap>
              <Tag color="processing">分析已完成</Tag>
              <span>
                输出语言：
                {job.output_language === 'zh-CN' ? '简体中文' : 'English'}
              </span>
              <Button icon={<ReloadOutlined />} onClick={state.restart}>
                重新分析
              </Button>
            </Flex>
          </Flex>
          <AnalysisResultView result={job.result} />
        </>
      ) : (
        <section
          aria-live="polite"
          className={styles.job}
          style={{ padding: screens.sm ? 28 : 20 }}
        >
          <Flex align="flex-start" justify="space-between">
            <div className={styles.jobHeading}>
              <span>分析状态</span>
              <Typography.Title level={2}>
                {statusLabels[job.status]}
              </Typography.Title>
            </div>
            <Tag color={job.status === 'failed' ? 'red' : 'blue'}>
              第 {job.attempt} 次尝试
            </Tag>
          </Flex>
          <Progress percent={job.progress} status="active" />
          <p>当前阶段：{job.stage ? stageLabels[job.stage] : '—'}</p>
          {job.status === 'failed' ? (
            <Alert
              showIcon
              title={`错误代码：${job.error_code ?? 'unknown_error'}`}
              type="info"
            />
          ) : null}
          <Space wrap>
            {cancellableAnalysisStatuses.has(job.status) ? (
              <Button
                aria-label="取消分析"
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
        </section>
      )}
      {job?.status === 'succeeded' && !job.result ? (
        <Alert showIcon title="分析结果暂不可用" type="warning" />
      ) : null}
    </ProCard>
  );
}
