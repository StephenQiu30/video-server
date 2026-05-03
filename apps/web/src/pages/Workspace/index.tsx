import { DownloadOutlined, LinkOutlined, ReloadOutlined, SafetyOutlined } from '@ant-design/icons';
import { history } from '@@/core/history';
import { PageContainer, ProCard, ProForm, ProFormText } from '@ant-design/pro-components';
import { Alert, Button, Empty, List, Progress, Space, Typography, message } from 'antd';
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

function formatSize(size?: number) {
  if (!size) return '-';
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatDateTime(value?: string) {
  return value ? value.replace('T', ' ').slice(0, 19) : '-';
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

function canDownload(task: API.Task) {
  return task.state === 'succeeded' && !isExpiredTask(task);
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
    return [...active, ...recent].slice(0, 4);
  }, [visibleTasks]);

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

  const openTaskDetail = (task: API.Task) => {
    setSelectedTask(task);
    setDrawerOpen(true);
  };

  const renderTaskActions = (task: API.Task) => (
    <Space>
      <Button type="link" onClick={() => openTaskDetail(task)}>
        查看
      </Button>
      <Button
        type="link"
        icon={<DownloadOutlined />}
        disabled={!canDownload(task)}
        loading={downloadingTaskId === task.id}
        onClick={() => handleDownload(task)}
      >
        下载文件
      </Button>
    </Space>
  );

  return (
    <PageContainer title={false}>
      <div className="download-workspace">
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <ProCard bordered>
            <Space direction="vertical" size={20} style={{ width: '100%' }}>
              <Space direction="vertical" size={4} style={{ width: '100%', textAlign: 'center' }}>
                <Typography.Title level={2} style={{ margin: 0 }}>
                  视频下载器
                </Typography.Title>
                <Typography.Text type="secondary">粘贴公开视频链接，解析后创建本机下载任务</Typography.Text>
              </Space>

              <ProForm
                layout="vertical"
                submitter={{
                  searchConfig: { submitText: '解析链接', resetText: '重置' },
                  resetButtonProps: { disabled: parsing || Boolean(creatingFormatId) },
                  submitButtonProps: {
                    icon: <LinkOutlined />,
                    loading: parsing,
                    disabled: Boolean(creatingFormatId),
                  },
                }}
                onReset={() => {
                  setParsed(undefined);
                  setParseError(undefined);
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
                  fieldProps={{ size: 'large', allowClear: true }}
                  rules={[{ required: true, message: '请输入视频链接' }]}
                />
              </ProForm>

              {parseError ? <Alert type="error" showIcon message={parseError} /> : null}

              {parsed ? (
                <List
                  className="download-format-list"
                  header={
                    <Space direction="vertical" size={4}>
                      <Typography.Text strong>{parsed.title || '解析结果'}</Typography.Text>
                      <Typography.Text type="secondary">
                        时长：{formatDuration(parsed.duration_seconds)} / 来源：{parsed.url}
                      </Typography.Text>
                    </Space>
                  }
                  dataSource={parsed.formats.length ? parsed.formats : [{ format_id: 'best', label: '最佳可用格式' }]}
                  renderItem={(format, index) => (
                    <List.Item
                      actions={[
                        <Button
                          key="create"
                          type={index === 0 ? 'primary' : 'default'}
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
            </Space>
          </ProCard>

          <ProCard
            title="任务状态"
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
            <List
              dataSource={keyTasks}
              locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无下载任务" /> }}
              renderItem={(task) => (
                <List.Item className="download-task-item" actions={[renderTaskActions(task)]}>
                  <List.Item.Meta
                    title={
                      <Space direction="vertical" size={4} style={{ width: '100%' }}>
                        <Typography.Text strong ellipsis>
                          {task.title || task.output_filename || '未命名视频'}
                        </Typography.Text>
                        <Space wrap>
                          <TaskStateTag state={task.state} />
                          {isExpiredTask(task) ? <Typography.Text type="warning">文件已过期</Typography.Text> : null}
                        </Space>
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size={8} style={{ width: '100%' }}>
                        <Progress
                          percent={task.progress}
                          size="small"
                          strokeColor="#1677ff"
                          status={task.state === 'failed' ? 'exception' : undefined}
                        />
                        {canDownload(task) ? (
                          <div className="download-ready-info">
                            <Typography.Text strong>文件已准备好</Typography.Text>
                            <Typography.Text type="secondary">
                              文件：{task.output_filename || '-'} / 大小：{formatSize(task.object_size)} / 过期时间：
                              {formatDateTime(task.expires_at)}
                            </Typography.Text>
                          </div>
                        ) : null}
                        {task.failure_reason ? <Typography.Text type="danger">{task.failure_reason}</Typography.Text> : null}
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </ProCard>

          <Alert
            type="info"
            showIcon
            icon={<SafetyOutlined />}
            message="MVP 不支持 Cookie 托管、DRM 规避、付费墙绕过、会员内容绕过和平台专用解析。"
          />
        </Space>
      </div>
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
