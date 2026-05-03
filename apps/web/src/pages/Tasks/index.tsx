import { DownloadOutlined, ReloadOutlined, StopOutlined } from '@ant-design/icons';
import { PageContainer, ProTable, type ProColumns } from '@ant-design/pro-components';
import { Button, Space, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { TaskDetailDrawer } from '../../components/TaskDetailDrawer';
import { TaskStateTag } from '../../components/TaskStateTag';
import { cancelTask, listTasks, openTaskDownload, retryTask } from '../../services/api';

function canRetry(task: API.Task) {
  return task.state === 'failed' || task.state === 'canceled' || Boolean(task.failure_code === 'retention_expired');
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<API.Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState<API.Task>();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      setTasks(await listTasks());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

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
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'state',
      width: 120,
      render: (_, record) => <TaskStateTag state={record.state} />,
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
          disabled={record.state !== 'succeeded'}
          onClick={async () => {
            await openTaskDownload(record.id);
          }}
        >
          下载
        </Button>,
        <Button
          key="retry"
          type="link"
          icon={<ReloadOutlined />}
          disabled={!canRetry(record)}
          onClick={async () => {
            await retryTask(record.id);
            message.success('重试任务已创建');
            await refresh();
          }}
        >
          重试
        </Button>,
        <Button
          key="cancel"
          type="link"
          danger
          icon={<StopOutlined />}
          disabled={record.state !== 'queued' && record.state !== 'running'}
          onClick={async () => {
            await cancelTask(record.id);
            message.success('任务已取消');
            await refresh();
          }}
        >
          取消
        </Button>,
      ],
    },
  ];

  return (
    <PageContainer
      title="任务历史"
      subTitle="查看下载状态、失败原因和文件入口"
      extra={<Button icon={<ReloadOutlined />} onClick={refresh}>刷新</Button>}
    >
      <ProTable<API.Task>
        rowKey="id"
        search={false}
        loading={loading}
        columns={columns}
        dataSource={tasks}
        pagination={{ pageSize: 8 }}
      />
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
