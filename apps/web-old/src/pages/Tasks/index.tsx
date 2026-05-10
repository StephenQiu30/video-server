import { DownloadOutlined, ReloadOutlined, StopOutlined } from '@ant-design/icons';
import { PageContainer, ProTable, ProList, type ProColumns } from '@ant-design/pro-components';
import { Button, Grid, Progress, Space, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { TaskDetailDrawer } from '../../components/TaskDetailDrawer';
import { TaskStateTag } from '../../components/TaskStateTag';
import { API_BASE_URL, cancelTask, listTasks, openTaskDownload, retryTask } from '../../services/api';
import { formatDateTime, formatSize } from '../../utils/format';

function canRetry(task: API.Task) {
  return task.is_latest_attempt !== false && (task.state === 'failed' || task.state === 'canceled' || Boolean(task.failure_code === 'retention_expired'));
}

function canDownload(task: API.Task) {
  return task.state === 'succeeded' && task.failure_code !== 'retention_expired';
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

export default function TasksPage() {
  const screens = Grid.useBreakpoint();
  const [tasks, setTasks] = useState<API.Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<string>();
  const [selectedTask, setSelectedTask] = useState<API.Task>();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const refresh = useCallback(async (showError = true) => {
    setLoading(true);
    try {
      setTasks(await listTasks({ limit: 200 }));
    } catch (error) {
      if (showError) {
        message.error(error instanceof Error ? error.message : '任务历史刷新失败');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    let fallbackTimer: ReturnType<typeof setInterval> | undefined;
    const stopStream = subscribeTaskSnapshots(
      200,
      (nextTasks) => {
        setTasks(nextTasks);
        setLoading(false);
        if (fallbackTimer) {
          clearInterval(fallbackTimer);
          fallbackTimer = undefined;
        }
      },
      () => {
        if (!fallbackTimer) {
          fallbackTimer = setInterval(() => refresh(false), 5000);
        }
      },
    );
    return () => {
      stopStream();
      if (fallbackTimer) clearInterval(fallbackTimer);
    };
  }, [refresh]);

  useEffect(() => {
    if (!selectedTask) return;
    const latest = tasks.find((task) => task.id === selectedTask.id);
    if (latest) setSelectedTask(latest);
  }, [selectedTask?.id, tasks]);

  const columns: ProColumns<API.Task>[] = [
    {
      title: '视频',
      dataIndex: 'title',
      render: (_, record) => (
        <Space direction="vertical" size={2}>
          <Typography.Text strong ellipsis style={{ maxWidth: 360 }}>
            {record.title || record.output_filename || '未命名视频'}
          </Typography.Text>
          <Typography.Text type="secondary" ellipsis style={{ maxWidth: 360 }}>
            {record.source_url}
          </Typography.Text>
          <Space size={4} wrap>
            {record.attempt_no > 1 ? <Tag color="blue">第 {record.attempt_no} 次尝试</Tag> : null}
            {record.is_latest_attempt === false ? <Tag>已重试</Tag> : <Tag color="processing">最新任务</Tag>}
          </Space>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'state',
      width: 120,
      valueEnum: {
        queued: { text: '排队中' },
        running: { text: '进行中' },
        succeeded: { text: '已完成' },
        failed: { text: '失败' },
        canceled: { text: '已取消' },
      },
      filters: true,
      onFilter: (value, record) => record.state === value,
      render: (_, record) => (
        <Space direction="vertical" size={4}>
          <TaskStateTag state={record.state} />
          {record.failure_code === 'retention_expired' ? <Tag color="warning">文件已过期</Tag> : null}
        </Space>
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      width: 90,
      renderText: (value) => `${value}%`,
    },
    {
      title: '格式',
      dataIndex: 'format_label',
      width: 140,
      renderText: (_, record) => record.format_label || record.format_id || 'best',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      valueType: 'dateTime',
      width: 180,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 240,
      render: (_, record) => [
        <Button
          key="detail"
          type="link"
          onClick={() => {
            setSelectedTask(record);
            setDrawerOpen(true);
          }}
        >
          详情
        </Button>,
        <Button
          key="download"
          type="link"
          icon={<DownloadOutlined />}
          disabled={!canDownload(record)}
          loading={activeAction === `download:${record.id}`}
          onClick={async () => {
            setActiveAction(`download:${record.id}`);
            try {
              await openTaskDownload(record.id);
            } catch (error) {
              message.error(error instanceof Error ? error.message : '下载链接获取失败');
            } finally {
              setActiveAction(undefined);
            }
          }}
        >
          下载
        </Button>,
        <Button
          key="retry"
          type="link"
          icon={<ReloadOutlined />}
          disabled={!canRetry(record)}
          loading={activeAction === `retry:${record.id}`}
          onClick={async () => {
            setActiveAction(`retry:${record.id}`);
            try {
              await retryTask(record.id);
              message.success('重试任务已创建');
              await refresh();
            } catch (error) {
              message.error(error instanceof Error ? error.message : '重试任务创建失败');
            } finally {
              setActiveAction(undefined);
            }
          }}
        >
          {record.is_latest_attempt === false ? '已重试' : '重试'}
        </Button>,
        <Button
          key="cancel"
          type="link"
          danger
          icon={<StopOutlined />}
          disabled={record.state !== 'queued' && record.state !== 'running'}
          loading={activeAction === `cancel:${record.id}`}
          onClick={async () => {
            setActiveAction(`cancel:${record.id}`);
            try {
              await cancelTask(record.id);
              message.success('任务已取消');
              await refresh();
            } catch (error) {
              message.error(error instanceof Error ? error.message : '任务取消失败');
            } finally {
              setActiveAction(undefined);
            }
          }}
        >
          取消
        </Button>,
      ],
    },
  ];

  const renderActions = (record: API.Task) => (
    <Space wrap>
      <Button
        type="link"
        onClick={() => {
          setSelectedTask(record);
          setDrawerOpen(true);
        }}
      >
        详情
      </Button>
      <Button
        type="link"
        icon={<DownloadOutlined />}
        disabled={!canDownload(record)}
        loading={activeAction === `download:${record.id}`}
        onClick={async () => {
          setActiveAction(`download:${record.id}`);
          try {
            await openTaskDownload(record.id);
          } catch (error) {
            message.error(error instanceof Error ? error.message : '下载链接获取失败');
          } finally {
            setActiveAction(undefined);
          }
        }}
      >
        下载
      </Button>
      <Button
        type="link"
        icon={<ReloadOutlined />}
        disabled={!canRetry(record)}
        loading={activeAction === `retry:${record.id}`}
        onClick={async () => {
          setActiveAction(`retry:${record.id}`);
          try {
            await retryTask(record.id);
            message.success('重试任务已创建');
            await refresh();
          } catch (error) {
            message.error(error instanceof Error ? error.message : '重试任务创建失败');
          } finally {
            setActiveAction(undefined);
          }
        }}
      >
        {record.is_latest_attempt === false ? '已重试' : '重试'}
      </Button>
      <Button
        type="link"
        danger
        icon={<StopOutlined />}
        disabled={record.state !== 'queued' && record.state !== 'running'}
        loading={activeAction === `cancel:${record.id}`}
        onClick={async () => {
          setActiveAction(`cancel:${record.id}`);
          try {
            await cancelTask(record.id);
            message.success('任务已取消');
            await refresh();
          } catch (error) {
            message.error(error instanceof Error ? error.message : '任务取消失败');
          } finally {
            setActiveAction(undefined);
          }
        }}
      >
        取消
      </Button>
    </Space>
  );

  return (
    <PageContainer
      title="任务历史"
      subTitle="查看下载状态、失败原因和文件入口"
      extra={<Button icon={<ReloadOutlined />} onClick={() => refresh()}>刷新</Button>}
    >
      {screens.md ? (
        <ProTable<API.Task>
          rowKey="id"
          search={false}
          loading={loading}
          columns={columns}
          dataSource={tasks}
          pagination={{ pageSize: 10, showSizeChanger: true }}
        />
      ) : (
        <ProList<API.Task>
          rowKey="id"
          loading={loading}
          dataSource={tasks}
          pagination={{ pageSize: 8, size: 'small' }}
          metas={{
            title: {
              render: (_, record) => (
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Typography.Text strong>{record.title || record.output_filename || '未命名视频'}</Typography.Text>
                  <Typography.Text type="secondary" ellipsis>
                    {record.source_url}
                  </Typography.Text>
                </Space>
              ),
            },
            subTitle: {
              render: (_, record) => (
                <Space wrap>
                  <TaskStateTag state={record.state} />
                  {record.failure_code === 'retention_expired' ? <Tag color="warning">文件已过期</Tag> : null}
                  {record.attempt_no > 1 ? <Tag color="blue">第 {record.attempt_no} 次尝试</Tag> : null}
                  {record.is_latest_attempt === false ? <Tag>已重试</Tag> : <Tag color="processing">最新任务</Tag>}
                  <Typography.Text type="secondary">格式：{record.format_label || record.format_id || 'best'}</Typography.Text>
                </Space>
              ),
            },
            description: {
              render: (_, record) => (
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  <Progress percent={record.progress} size="small" strokeColor="#1677ff" />
                  {canDownload(record) ? (
                    <Typography.Text type="secondary">
                      文件：{record.output_filename || '-'} / 大小：{formatSize(record.object_size)} / 过期时间：
                      {formatDateTime(record.expires_at)}
                    </Typography.Text>
                  ) : null}
                  {record.failure_reason ? <Typography.Text type="danger">{record.failure_reason}</Typography.Text> : null}
                </Space>
              ),
            },
            actions: {
              render: (_, record) => renderActions(record),
            },
          }}
        />
      )}
      <TaskDetailDrawer
        task={selectedTask}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onChanged={async () => {
          setDrawerOpen(false);
          await refresh();
        }}
      />
    </PageContainer>
  );
}
