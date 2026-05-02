import { DownloadOutlined, StopOutlined } from '@ant-design/icons';
import { Button, Descriptions, Drawer, Progress, Space, Typography, message } from 'antd';
import { cancelTask, getDownloadLink } from '../services/api';
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

export function TaskDetailDrawer({ task, open, onClose, onChanged }: Props) {
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
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="任务 ID">{task.id}</Descriptions.Item>
            <Descriptions.Item label="格式">{task.format_label || task.format_id || 'best'}</Descriptions.Item>
            <Descriptions.Item label="文件">{task.output_filename || '-'}</Descriptions.Item>
            <Descriptions.Item label="大小">{formatSize(task.object_size)}</Descriptions.Item>
            <Descriptions.Item label="过期时间">{task.expires_at || '-'}</Descriptions.Item>
            <Descriptions.Item label="失败原因">{task.failure_reason || '-'}</Descriptions.Item>
          </Descriptions>
          <Space>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              disabled={task.state !== 'succeeded'}
              onClick={async () => {
                const result = await getDownloadLink(task.id);
                window.open(result.url, '_blank', 'noopener,noreferrer');
              }}
            >
              获取下载链接
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
