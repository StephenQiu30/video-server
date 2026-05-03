import { DownloadOutlined, LinkOutlined, ReloadOutlined, SafetyOutlined } from '@ant-design/icons';
import { history } from '@@/core/history';
import { PageContainer, ProCard, ProForm, ProFormText } from '@ant-design/pro-components';
import { Alert, Button, Empty, List, Progress, Row, Col, Space, Typography, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { TaskDetailDrawer } from '../../components/TaskDetailDrawer';
import { TaskStateTag } from '../../components/TaskStateTag';
import { createTask, listTasks, normalizeUserUrl, openTaskDownload, parseVideo } from '../../services/api';

function formatDuration(seconds?: number) {
  if (!seconds) return '-';
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}:${String(rest).padStart(2, '0')}`;
}

function isSmokeTask(task: API.Task) {
  const title = task.title || task.output_filename || '';
  return /^\[Smoke\]/i.test(title) || ['Smoke Sample', 'Negative State', 'Negative Ownership', 'Download Acceptance'].includes(title);
}

function isActiveTask(task: API.Task) {
  return task.state === 'queued' || task.state === 'running';
}

function isExpiredTask(task: API.Task) {
  return task.failure_code === 'retention_expired';
}

function formatSize(size?: number) {
  if (!size) return '-';
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export default function WorkspacePage() {
  const [parsing, setParsing] = useState(false);
  const [creatingFormatId, setCreatingFormatId] = useState<string>();
  const [downloadingTaskId, setDownloadingTaskId] = useState<string>();
  const [tasks, setTasks] = useState<API.Task[]>([]);
  const [parsed, setParsed] = useState<API.ParseResponse>();
  const [parseError, setParseError] = useState<string>();
  const [selectedTask, setSelectedTask] = useState<API.Task>();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const refreshTasks = async () => {
    try {
      setTasks(await listTasks({ limit: 20 }));
    } catch (error) {
      message.error(error instanceof Error ? error.message : '任务列表刷新失败');
    }
  };

  useEffect(() => {
    refreshTasks();
  }, []);

  const visibleTasks = useMemo(() => tasks.filter((task) => !isSmokeTask(task)), [tasks]);
  const keyTasks = useMemo(() => {
    const active = visibleTasks.filter(isActiveTask);
    const recent = visibleTasks.filter((task) => !isActiveTask(task));
    return [...active, ...recent].slice(0, 3);
  }, [visibleTasks]);
  const currentTask = keyTasks[0];

  const handleDownload = async (task: API.Task) => {
    setDownloadingTaskId(task.id);
    try {
      await openTaskDownload(task.id);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '下载链接获取失败');
    } finally {
      setDownloadingTaskId(undefined);
    }
  };

  const renderTaskActions = (task: API.Task) => {
    const expired = isExpiredTask(task);
    return (
      <Space>
        <Button
          type="link"
          onClick={() => {
            setSelectedTask(task);
            setDrawerOpen(true);
          }}
        >
          查看
        </Button>
        <Button
          type="link"
          icon={<DownloadOutlined />}
          disabled={task.state !== 'succeeded' || expired}
          loading={downloadingTaskId === task.id}
          onClick={() => handleDownload(task)}
        >
          下载文件
        </Button>
      </Space>
    );
  };

  return (
    <PageContainer title="下载工作台" subTitle="解析公开视频链接，创建后台下载任务">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} xl={15}>
            <ProCard title="新建下载" bordered>
              <ProForm
                layout="vertical"
                submitter={{
                  searchConfig: { submitText: '解析链接' },
                  submitButtonProps: { icon: <LinkOutlined />, loading: parsing, disabled: Boolean(creatingFormatId) },
                }}
                onFinish={async (values) => {
                  let normalizedUrl: string;
                  setParseError(undefined);
                  try {
                    normalizedUrl = normalizeUserUrl(String(values.url || ''));
                    if (normalizedUrl !== String(values.url || '').trim()) {
                      message.info('已自动补全 https://');
                    }
                  } catch (error) {
                    const errorMessage = error instanceof Error ? error.message : '请输入有效的视频链接';
                    setParseError(errorMessage);
                    message.error(errorMessage);
                    return false;
                  }
                  setParsing(true);
                  setParsed(undefined);
                  try {
                    const result = await parseVideo(normalizedUrl);
                    setParsed(result);
                    setParseError(undefined);
                    message.success('解析完成');
                  } catch (error) {
                    const errorMessage = error instanceof Error ? error.message : '公开视频解析失败或平台暂不支持';
                    setParseError(errorMessage);
                    message.error(errorMessage);
                  } finally {
                    setParsing(false);
                  }
                  return true;
                }}
              >
                <ProFormText
                  name="url"
                  label="视频链接"
                  placeholder="https://example.com/video"
                  rules={[{ required: true, message: '请输入视频链接' }]}
                />
              </ProForm>

              {parseError ? <Alert type="error" showIcon message={parseError} style={{ marginBottom: 16 }} /> : null}

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
                          loading={creatingFormatId === format.format_id}
                          disabled={Boolean(creatingFormatId) || parsing}
                          onClick={async () => {
                            setCreatingFormatId(format.format_id);
                            try {
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
                            } catch (error) {
                              message.error(error instanceof Error ? error.message : '任务创建失败');
                            } finally {
                              setCreatingFormatId(undefined);
                            }
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
            <ProCard
              title="当前任务"
              bordered
              extra={
                <Space>
                  <Button icon={<ReloadOutlined />} onClick={refreshTasks} />
                  <Button type="link" onClick={() => history.push('/tasks')}>
                    完整历史
                  </Button>
                </Space>
              }
            >
              {currentTask ? (
                <Space direction="vertical" size={14} style={{ width: '100%' }}>
                  <Space direction="vertical" size={6} style={{ width: '100%' }}>
                    <Typography.Text strong ellipsis>
                      {currentTask.title || currentTask.output_filename || '未命名视频'}
                    </Typography.Text>
                    <TaskStateTag state={currentTask.state} />
                    <Progress percent={currentTask.progress} size="small" />
                  </Space>
                  {isExpiredTask(currentTask) ? (
                    <Alert type="warning" showIcon message="文件已过期，可在任务详情中重试任务" />
                  ) : null}
                  {currentTask.state === 'succeeded' && !isExpiredTask(currentTask) ? (
                    <Alert
                      type="success"
                      showIcon
                      message="文件已准备好"
                      description={`文件：${currentTask.output_filename || '-'} / 大小：${formatSize(currentTask.object_size)} / 过期时间：${currentTask.expires_at || '-'}`}
                    />
                  ) : null}
                  {renderTaskActions(currentTask)}
                </Space>
              ) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无当前任务" />
              )}
            </ProCard>

            <ProCard title="最近关键任务" bordered style={{ marginTop: 16 }}>
              <List
                dataSource={keyTasks.slice(1)}
                locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无更多任务" /> }}
                renderItem={(task) => (
                  <List.Item actions={[renderTaskActions(task)]}>
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
