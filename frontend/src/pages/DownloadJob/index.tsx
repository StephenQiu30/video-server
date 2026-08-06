import {
  CheckCircleOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Flex,
  Progress,
  Result,
  Spin,
  Typography,
} from 'antd';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { toProblem } from '@/utils/problem';
import { formatBytes, isExpired } from '@/utils/videoData';
import { openDownloadUrl, useDownloadJob, useDownloadUrl } from './hooks';

type ArtifactSummary = {
  fileName: string;
  contentType: string;
  sizeBytes: number | null;
  sha256: string | null;
  expiresAt: string | null;
};

function parseArtifact(value: unknown): ArtifactSummary | null {
  if (typeof value !== 'object' || value === null) return null;
  const data = value as Record<string, unknown>;
  if (
    typeof data.file_name !== 'string' ||
    typeof data.content_type !== 'string'
  )
    return null;
  return {
    fileName: data.file_name,
    contentType: data.content_type,
    sizeBytes: typeof data.size_bytes === 'number' ? data.size_bytes : null,
    sha256: typeof data.sha256 === 'string' ? data.sha256 : null,
    expiresAt: typeof data.expires_at === 'string' ? data.expires_at : null,
  };
}

const statusLabel: Record<string, string> = {
  queued: '排队中',
  running: '处理中',
  succeeded: '已完成',
  failed: '处理失败',
  expired: '文件已过期',
};

export default function DownloadJobPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [online, setOnline] = useState(() => navigator.onLine);
  const query = useDownloadJob(jobId);
  const downloadUrl = useDownloadUrl(jobId);
  const job = query.data;
  const artifact = parseArtifact(job?.artifact);

  useEffect(() => {
    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  useEffect(() => {
    document.title = jobId ? `下载任务 ${jobId.slice(0, 8)}` : '下载任务';
    return () => {
      document.title = '公开视频下载器';
    };
  }, [jobId]);

  const fetchFile = async () => {
    const result = await downloadUrl.request();
    if (!result) return;
    if (result.expiresAt && isExpired(result.expiresAt)) return;
    openDownloadUrl(result.url);
  };

  if (!jobId) {
    return (
      <Result
        status="error"
        title="任务链接无效"
        subTitle="请从有效的下载任务链接进入。"
      />
    );
  }

  return (
    <main
      style={{ minHeight: '100vh', padding: 'clamp(24px, 8vw, 96px) 16px' }}
    >
      <Card style={{ margin: '0 auto', maxWidth: 760 }}>
        <Flex vertical gap={20}>
          <Typography.Title level={2} style={{ marginTop: 0 }}>
            下载任务
          </Typography.Title>
          {!online ? (
            <Alert
              type="warning"
              showIcon
              title="当前处于离线状态"
              description="网络恢复后会继续查询任务状态。"
            />
          ) : null}
          {query.isLoading ? (
            <Flex align="center" gap={12} aria-live="polite">
              <Spin /> 正在读取任务状态
            </Flex>
          ) : null}
          {query.isError && !job ? (
            <Result
              status="error"
              icon={<ExclamationCircleOutlined />}
              title={toProblem(query.error).title}
              subTitle={toProblem(query.error).detail}
            />
          ) : null}
          {job?.status === 'queued' ? (
            <Result
              status="info"
              title="任务排队中"
              subTitle="任务正在等待处理，不需要手动刷新。"
            />
          ) : null}
          {job?.status === 'running' ? (
            <Card size="small" aria-live="polite">
              <Typography.Title level={3}>正在处理</Typography.Title>
              <Typography.Paragraph type="secondary">
                {job.stage ?? '正在准备视频文件'}
              </Typography.Paragraph>
              {job.progressPercent === null ? (
                <Typography.Text>进度暂不可确定</Typography.Text>
              ) : (
                <Progress
                  percent={Math.min(100, Math.max(0, job.progressPercent))}
                  status="active"
                />
              )}
            </Card>
          ) : null}
          {job?.status === 'succeeded' && artifact ? (
            <Result
              status="success"
              icon={<CheckCircleOutlined />}
              title="视频已准备好"
              subTitle="点击按钮后才会获取临时下载地址。"
              extra={
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  loading={downloadUrl.isPending}
                  onClick={fetchFile}
                >
                  获取文件
                </Button>
              }
            >
              <Descriptions column={1} size="small" bordered>
                <Descriptions.Item label="文件名">
                  {artifact.fileName}
                </Descriptions.Item>
                <Descriptions.Item label="类型">
                  {artifact.contentType}
                </Descriptions.Item>
                <Descriptions.Item label="大小">
                  {formatBytes(artifact.sizeBytes)}
                </Descriptions.Item>
                {artifact.sha256 ? (
                  <Descriptions.Item label="SHA-256">
                    <Typography.Text copyable>
                      {artifact.sha256}
                    </Typography.Text>
                  </Descriptions.Item>
                ) : null}
                {artifact.expiresAt ? (
                  <Descriptions.Item label="文件过期时间">
                    {new Date(artifact.expiresAt).toLocaleString()}
                  </Descriptions.Item>
                ) : null}
              </Descriptions>
            </Result>
          ) : null}
          {job?.status === 'succeeded' && !artifact ? (
            <Result
              status="error"
              title="文件信息不可用"
              subTitle="服务端返回的数据不完整，请稍后重试。"
            />
          ) : null}
          {job?.status === 'failed' ? (
            <Result
              status="error"
              title="下载失败"
              subTitle={toProblem(job.error).detail}
            />
          ) : null}
          {job?.status === 'expired' ? (
            <Result
              status="warning"
              title="文件已过期"
              subTitle="请重新解析视频并创建新的下载任务。"
            />
          ) : null}
          {job && !statusLabel[job.status] ? (
            <Result
              status="error"
              title="任务状态未知"
              subTitle="无法安全展示此任务状态。"
            />
          ) : null}
          {downloadUrl.problem ? (
            <Alert
              type="error"
              showIcon
              title={downloadUrl.problem.title}
              description={downloadUrl.problem.detail}
            />
          ) : null}
          {query.isError && job ? (
            <Alert
              type="warning"
              showIcon
              title="状态刷新暂时失败"
              description="已保留最近一次真实状态，网络恢复后会继续尝试。"
            />
          ) : null}
        </Flex>
      </Card>
    </main>
  );
}
