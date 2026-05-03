import { DownloadOutlined, ReloadOutlined, StopOutlined } from '@ant-design/icons';
import { Alert, Button, Descriptions, Drawer, Progress, Space, Timeline, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { cancelTask, listTaskEvents, openTaskDownload, retryTask } from '../services/api';
import { TaskStateTag } from './TaskStateTag';

type Props = {
  task?: API.Task;
  open: boolean;
  onClose: () => void;
  onChanged: () => void;
};

function formatSize(size?: number) {
  if (!size) return '-';
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function canRetry(task: API.Task) {
  return task.state === 'failed' || task.state === 'canceled' || Boolean(task.failure_code === 'retention_expired');
}

export function TaskDetailDrawer({ task, open, onClose, onChanged }: Props) {
  const [events, setEvents] = useState<API.TaskEvent[]>([]);

  useEffect(() => {
    if (!open || !task) {
      setEvents([]);
      return;
    }
    listTaskEvents(task.id).then(setEvents).catch(() => setEvents([]));
  }, [open, task?.id]);

  return (
    <Drawer title="任务详情" width={520} open={open} onClose={onClose}>
      {task ? (
        <Space direction="vertical" size={18} style={{ width: '100%' }}>
          <Space direction="vertical" size={6}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              {task.title || task.output_filename || '未命名视频'}
            </Typography.Title>
            <TaskStateTag state={task.state} />
          </Space>
          <Progress percent={task.progress} status={task.state === 'failed' ? 'exception' : undefined} />
          {task.failure_reason ? <Alert type="warning" showIcon message={task.failure_reason} /> : null}
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="任务 ID">{task.id}</Descriptions.Item>
            <Descriptions.Item label="格式">{task.format_label || task.format_id || 'best'}</Descriptions.Item>
            <Descriptions.Item label="文件">{task.output_filename || '-'}</Descriptions.Item>
            <Descriptions.Item label="大小">{formatSize(task.object_size)}</Descriptions.Item>
            <Descriptions.Item label="过期时间">{task.expires_at || '-'}</Descriptions.Item>
            <Descriptions.Item label="失败代码">{task.failure_code || '-'}</Descriptions.Item>
          </Descriptions>
          <Timeline
            items={events.map((event) => ({
              color: event.state === 'failed' ? 'red' : event.state === 'succeeded' ? 'green' : 'blue',
              children: (
                <Space direction="vertical" size={2}>
                  <Typography.Text>{event.message || event.state}</Typography.Text>
                  <Typography.Text type="secondary">{event.created_at}</Typography.Text>
                </Space>
              ),
            }))}
          />
          <Space>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              disabled={task.state !== 'succeeded'}
              onClick={async () => {
                await openTaskDownload(task.id);
              }}
            >
              下载文件
            </Button>
            <Button
              icon={<ReloadOutlined />}
              disabled={!canRetry(task)}
              onClick={async () => {
                await retryTask(task.id);
                message.success('重试任务已创建');
                onChanged();
              }}
            >
              重试
            </Button>
            <Button
              icon={<StopOutlined />}
              disabled={task.state !== 'queued' && task.state !== 'running'}
              onClick={async () => {
                await cancelTask(task.id);
                message.success('任务已取消');
                onChanged();
              }}
            >
              取消任务
            </Button>
          </Space>
        </Space>
      ) : null}
    </Drawer>
  );
}
