import { CloudDownloadOutlined, LinkOutlined, ReloadOutlined, SafetyOutlined } from '@ant-design/icons';
import { PageContainer, ProCard, ProForm, ProFormText, StatisticCard } from '@ant-design/pro-components';
import { Button, Empty, List, Progress, Row, Col, Space, Typography, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { TaskDetailDrawer } from '../../components/TaskDetailDrawer';
import { TaskStateTag } from '../../components/TaskStateTag';
import { createTask, listTasks, parseVideo } from '../../services/api';

function formatDuration(seconds?: number) {
  if (!seconds) return '-';
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}:${String(rest).padStart(2, '0')}`;
}

export default function WorkspacePage() {
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<API.Task[]>([]);
  const [parsed, setParsed] = useState<API.ParseResponse>();
  const [selectedTask, setSelectedTask] = useState<API.Task>();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const refreshTasks = async () => {
    setTasks(await listTasks());
  };

  useEffect(() => {
    refreshTasks();
  }, []);

  const stats = useMemo(() => {
    return {
      total: tasks.length,
      running: tasks.filter((item) => item.state === 'queued' || item.state === 'running').length,
      succeeded: tasks.filter((item) => item.state === 'succeeded').length,
      failed: tasks.filter((item) => item.state === 'failed').length,
    };
  }, [tasks]);

  return (
    <PageContainer title="下载工作台" subTitle="解析公开视频链接，创建后台下载任务">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <StatisticCard.Group>
          <StatisticCard statistic={{ title: '全部任务', value: stats.total, prefix: <CloudDownloadOutlined /> }} />
          <StatisticCard statistic={{ title: '进行中', value: stats.running, status: 'processing' }} />
          <StatisticCard statistic={{ title: '已完成', value: stats.succeeded, status: 'success' }} />
          <StatisticCard statistic={{ title: '失败', value: stats.failed, status: 'error' }} />
        </StatisticCard.Group>

        <Row gutter={[16, 16]}>
          <Col xs={24} xl={15}>
            <ProCard title="新建下载" bordered>
              <ProForm
                layout="vertical"
                submitter={{
                  searchConfig: { submitText: '解析链接' },
                  submitButtonProps: { icon: <LinkOutlined />, loading },
                }}
                onFinish={async (values) => {
                  setLoading(true);
                  try {
                    const result = await parseVideo(values.url);
                    setParsed(result);
                    message.success('解析完成');
                  } finally {
                    setLoading(false);
                  }
                }}
              >
                <ProFormText
                  name="url"
                  label="视频链接"
                  placeholder="https://example.com/video"
                  rules={[{ required: true, message: '请输入视频链接' }]}
                />
              </ProForm>

              {parsed ? (
                <List
                  header={
                    <Space direction="vertical" size={4}>
                      <Typography.Text strong>{parsed.title || '解析结果'}</Typography.Text>
                      <Typography.Text type="secondary">
                        时长：{formatDuration(parsed.duration_seconds)} / 来源：{parsed.url}
                      </Typography.Text>
                    </Space>
                  }
                  dataSource={parsed.formats.length ? parsed.formats : [{ format_id: 'best', label: '最佳可用格式' }]}
                  renderItem={(format) => (
                    <List.Item
                      actions={[
                        <Button
                          key="create"
                          type="primary"
                          onClick={async () => {
                            await createTask({
                              url: parsed.url,
                              title: parsed.title,
                              cover_url: parsed.cover_url,
                              duration_seconds: parsed.duration_seconds,
                              format_id: format.format_id,
                              format_label: format.label,
                            });
                            message.success('任务已创建');
                            await refreshTasks();
                          }}
                        >
                          创建任务
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={format.label || format.format_id}
                        description={[format.ext, format.resolution].filter(Boolean).join(' / ') || '默认格式'}
                      />
                    </List.Item>
                  )}
                />
              ) : null}
            </ProCard>
          </Col>

          <Col xs={24} xl={9}>
            <ProCard title="最近任务" bordered extra={<Button icon={<ReloadOutlined />} onClick={refreshTasks} />}>
              <List
                dataSource={tasks.slice(0, 5)}
                locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无任务" /> }}
                renderItem={(task) => (
                  <List.Item
                    actions={[
                      <Button
                        key="detail"
                        type="link"
                        onClick={() => {
                          setSelectedTask(task);
                          setDrawerOpen(true);
                        }}
                      >
                        查看
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={<Typography.Text ellipsis>{task.title || task.output_filename || task.id}</Typography.Text>}
                      description={
                        <Space direction="vertical" size={6} style={{ width: '100%' }}>
                          <TaskStateTag state={task.state} />
                          <Progress percent={task.progress} size="small" showInfo={false} />
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            </ProCard>
          </Col>
        </Row>

        <ProCard bordered>
          <Space>
            <SafetyOutlined />
            <Typography.Text>
              MVP 不支持 Cookie 托管、DRM 规避、付费墙绕过、会员内容绕过和平台专用解析。
            </Typography.Text>
          </Space>
        </ProCard>
      </Space>
      <TaskDetailDrawer
        task={selectedTask}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onChanged={async () => {
          setDrawerOpen(false);
          await refreshTasks();
        }}
      />
    </PageContainer>
  );
}
