import { DownloadOutlined, LinkOutlined, ReloadOutlined } from '@ant-design/icons';
import { history } from '@@/core/history';
import { PageContainer, ProCard, ProForm, ProFormText } from '@ant-design/pro-components';
import { Alert, Button, Empty, List, Progress, Radio, Space, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { TaskDetailDrawer } from './TaskDetailDrawer';
import { TaskStateTag } from './TaskStateTag';
import { API_BASE_URL, createTask, listTasks, normalizeUserUrl, openTaskDownload, parseVideo } from '../services/api';

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

function isLatestAttempt(task: API.Task) {
  return task.is_latest_attempt !== false;
}

function isExpiredTask(task: API.Task) {
  return task.failure_code === 'retention_expired';
}

function canDownload(task: API.Task) {
  return task.state === 'succeeded' && !isExpiredTask(task);
}

function subscribeTaskSnapshots(limit: number, onTasks: (tasks: API.Task[]) => void, onError: () => void) {
  if (typeof EventSource === 'undefined') {
    onError();
    return () => {};
  }
  const query = new URLSearchParams({ limit: String(limit) });
  const source = new EventSource(`${API_BASE_URL}/api/tasks/stream?${query.toString()}`);
  source.addEventListener('tasks', (event) => {
    try {
      const payload = JSON.parse((event as MessageEvent).data) as { tasks?: API.Task[] };
      onTasks(payload.tasks || []);
    } catch {
      onError();
    }
  });
  source.onerror = onError;
  return () => source.close();
}

export function DownloaderPage() {
  const [parsing, setParsing] = useState(false);
  const [creatingFormatId, setCreatingFormatId] = useState<string>();
  const [downloadingTaskId, setDownloadingTaskId] = useState<string>();
  const [tasks, setTasks] = useState<API.Task[]>([]);
  const [parsed, setParsed] = useState<API.ParseResponse>();
  const [parseError, setParseError] = useState<string>();
  const [selectedFormatId, setSelectedFormatId] = useState<string>();
  const [selectedTask, setSelectedTask] = useState<API.Task>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const refreshTasks = useCallback(async (showError = true) => {
    try {
      setTasks(await listTasks({ limit: 20 }));
    } catch (error) {
      if (showError) {
        message.error(error instanceof Error ? error.message : '任务列表刷新失败');
      }
    }
  }, []);

  useEffect(() => {
    refreshTasks();
    let fallbackTimer: ReturnType<typeof setInterval> | undefined;
    const stopStream = subscribeTaskSnapshots(
      20,
      (nextTasks) => {
        setTasks(nextTasks);
        if (fallbackTimer) {
          clearInterval(fallbackTimer);
          fallbackTimer = undefined;
        }
      },
      () => {
        if (!fallbackTimer) {
          fallbackTimer = setInterval(() => refreshTasks(false), 5000);
        }
      },
    );
    return () => {
      stopStream();
      if (fallbackTimer) clearInterval(fallbackTimer);
    };
  }, [refreshTasks]);

  useEffect(() => {
    if (!selectedTask) return;
    const latest = tasks.find((task) => task.id === selectedTask.id);
    if (latest) setSelectedTask(latest);
  }, [selectedTask?.id, tasks]);

  const keyTasks = useMemo(() => {
    const visibleTasks = tasks.filter((task) => !isSmokeTask(task) && isLatestAttempt(task));
    const active = visibleTasks.filter(isActiveTask);
    const recent = visibleTasks.filter((task) => !isActiveTask(task));
    return [...active, ...recent].slice(0, 4);
  }, [tasks]);

  const presetFormats = useMemo(() => {
    if (!parsed) return [];
    const presets = parsed.formats.filter((format) => format.kind !== 'raw');
    return presets.length ? presets : [{ format_id: 'best', label: '推荐下载', quality_label: '推荐', available: true }];
  }, [parsed]);

  const selectedFormat = useMemo(
    () => presetFormats.find((format) => format.format_id === selectedFormatId),
    [presetFormats, selectedFormatId],
  );

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
    <Space wrap>
      <Button type="link" onClick={() => openTaskDetail(task)}>
        详情
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
                <Typography.Text type="secondary">粘贴视频链接，解析后创建本机下载任务</Typography.Text>
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
                  setSelectedFormatId(undefined);
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
                  setSelectedFormatId(undefined);
                  try {
                    const result = await parseVideo(normalizedUrl);
                    setParsed(result);
                    const availablePreset = result.formats.find((format) => format.kind !== 'raw' && format.available !== false);
                    setSelectedFormatId(availablePreset?.format_id);
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
                  placeholder="https://www.bilibili.com/video/BV..."
                  fieldProps={{ size: 'large', allowClear: true }}
                  rules={[{ required: true, message: '请输入视频链接' }]}
                />
              </ProForm>

              {parseError ? <Alert type="error" showIcon message={parseError} /> : null}

              {parsed ? (
                <Space direction="vertical" size={16} style={{ width: '100%' }}>
                  <List
                    className="download-format-list"
                    header={
                      <Space direction="vertical" size={4}>
                        <Typography.Text strong>{parsed.title || '解析结果'}</Typography.Text>
                        <Typography.Text type="secondary">
                          时长：{formatDuration(parsed.duration_seconds)} / 来源：
                          {parsed.source_site || parsed.extractor || 'yt-dlp 可识别来源'}
                        </Typography.Text>
                        <Typography.Text type="secondary">先选择清晰度，再创建下载任务；清晰度越低通常文件更小，下载等待时间也更短。</Typography.Text>
                      </Space>
                    }
                    dataSource={presetFormats}
                    renderItem={(format, index) => {
                      const disabled = format.available === false;
                      const active = selectedFormatId === format.format_id;
                      return (
                        <List.Item
                          className={`download-format-option${active ? ' is-selected' : ''}${disabled ? ' is-disabled' : ''}`}
                          onClick={() => {
                            if (!disabled && !creatingFormatId && !parsing) {
                              setSelectedFormatId(format.format_id);
                            }
                          }}
                        >
                          <List.Item.Meta
                            avatar={<Radio checked={active} disabled={disabled} />}
                            title={
                              <Space wrap>
                                <Typography.Text strong>
                                  {index === 0 ? `推荐下载：${format.quality_label || format.label}` : format.quality_label || format.label}
                                </Typography.Text>
                                {disabled ? <Tag>不可用</Tag> : active ? <Tag color="blue">已选择</Tag> : <Tag color="processing">可选择</Tag>}
                              </Space>
                            }
                            description={
                              <Space direction="vertical" size={2}>
                                <Typography.Text type="secondary">
                                  {[format.ext, format.resolution].filter(Boolean).join(' / ') || format.label || '默认格式'}
                                </Typography.Text>
                                {format.note ? (
                                  <Typography.Text type={disabled ? 'warning' : 'secondary'}>{format.note}</Typography.Text>
                                ) : null}
                              </Space>
                            }
                          />
                        </List.Item>
                      );
                    }}
                  />
                  <Space wrap>
                    <Button
                      type="primary"
                      size="large"
                      loading={Boolean(creatingFormatId)}
                      disabled={!selectedFormat || selectedFormat.available === false || parsing}
                      onClick={async () => {
                        if (!selectedFormat) {
                          message.warning('请先选择清晰度');
                          return;
                        }
                        setCreatingFormatId(selectedFormat.format_id);
                        try {
                          await createTask({
                            url: parsed.url,
                            title: parsed.title,
                            cover_url: parsed.cover_url,
                            duration_seconds: parsed.duration_seconds,
                            format_id: selectedFormat.format_id,
                            format_label: selectedFormat.quality_label || selectedFormat.label,
                          });
                          message.success(`已创建 ${selectedFormat.quality_label || '推荐'} 下载任务`);
                          await refreshTasks();
                        } catch (error) {
                          message.error(error instanceof Error ? error.message : '任务创建失败');
                        } finally {
                          setCreatingFormatId(undefined);
                        }
                      }}
                    >
                      创建{selectedFormat?.quality_label ? ` ${selectedFormat.quality_label} ` : ''}下载任务
                    </Button>
                    <Typography.Text type="secondary">
                      当前选择：{selectedFormat?.quality_label || selectedFormat?.label || '未选择'}
                    </Typography.Text>
                  </Space>
                </Space>
              ) : null}
            </Space>
          </ProCard>

          <ProCard
            title="任务状态"
            bordered
            extra={
              <Space>
                <Button icon={<ReloadOutlined />} onClick={() => refreshTasks()} />
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
                          {task.attempt_no > 1 ? <Tag color="blue">第 {task.attempt_no} 次尝试</Tag> : null}
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
                          <Typography.Text type="secondary">
                            文件：{task.output_filename || '-'} / 大小：{formatSize(task.object_size)} / 过期时间：
                            {formatDateTime(task.expires_at)}
                          </Typography.Text>
                        ) : null}
                        {task.failure_reason ? <Typography.Text type="danger">{task.failure_reason}</Typography.Text> : null}
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </ProCard>

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
