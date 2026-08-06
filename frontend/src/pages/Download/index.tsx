import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Flex, Input, Result, Typography } from 'antd';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import LegalNotice from '@/components/LegalNotice';
import { validateVideoUrl } from '@/utils/url';
import FormatList from './components/FormatList';
import MediaSummary from './components/MediaSummary';
import { useInspectFlow } from './hooks';

export default function DownloadPage() {
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const {
    state,
    media,
    selectedFormatId,
    setSelectedFormatId,
    problem,
    createProblem,
    inspect,
    createDownload,
    isInspecting,
    isCreating,
  } = useInspectFlow();

  const submitInspect = () => {
    const error = validateVideoUrl(url);
    setValidationError(error);
    if (!error) void inspect(url.trim());
  };

  const selectedFormat =
    media?.formats.find((format) => format.id === selectedFormatId) ?? null;
  const create = async () => {
    const jobId = await createDownload(selectedFormat);
    if (jobId) navigate(`/downloads/${encodeURIComponent(jobId)}`);
  };

  return (
    <main
      style={{ minHeight: '100vh', padding: 'clamp(24px, 8vw, 96px) 16px' }}
    >
      <Card style={{ margin: '0 auto', maxWidth: 1000 }}>
        <Flex vertical gap={24}>
          <div>
            <Typography.Title level={1} style={{ marginTop: 0 }}>
              粘贴链接并下载
            </Typography.Title>
            <Typography.Paragraph type="secondary">
              输入公开视频链接，服务端解析后选择可用的清晰度。
            </Typography.Paragraph>
          </div>
          <Flex vertical gap={12} role="form" aria-label="视频链接表单">
            <Input
              aria-label="视频链接"
              placeholder="粘贴公开视频链接"
              value={url}
              status={validationError ? 'error' : undefined}
              onChange={(event) => {
                setUrl(event.target.value);
                if (validationError) setValidationError(null);
              }}
              onPressEnter={submitInspect}
              disabled={isInspecting}
            />
            {validationError ? (
              <Typography.Text type="danger">{validationError}</Typography.Text>
            ) : null}
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              loading={isInspecting}
              onClick={submitInspect}
            >
              {isInspecting ? '正在解析视频' : '解析视频'}
            </Button>
          </Flex>
          {state === 'inspect_failed' && problem ? (
            <Result
              status="error"
              title={problem.title}
              subTitle={problem.detail}
              extra={
                <Button icon={<ReloadOutlined />} onClick={submitInspect}>
                  重新解析
                </Button>
              }
            />
          ) : null}
          {state === 'expired' ? (
            <Alert
              type="warning"
              showIcon
              title="解析结果已过期"
              description="请重新解析链接后再选择清晰度。"
              action={<Button onClick={submitInspect}>重新解析</Button>}
            />
          ) : null}
          {state === 'inspected' && media ? (
            <Flex vertical gap={16} aria-live="polite">
              <MediaSummary media={media} />
              <Card size="small" title="选择清晰度">
                <FormatList
                  formats={media.formats}
                  value={selectedFormatId}
                  onChange={setSelectedFormatId}
                />
                <Button
                  type="primary"
                  block
                  style={{ marginTop: 16 }}
                  disabled={!selectedFormat}
                  loading={isCreating}
                  onClick={create}
                >
                  {isCreating ? '正在创建任务' : '开始下载'}
                </Button>
                {createProblem ? (
                  <Alert
                    style={{ marginTop: 12 }}
                    type="error"
                    showIcon
                    title={createProblem.title}
                    description={createProblem.detail}
                  />
                ) : null}
              </Card>
            </Flex>
          ) : null}
          <LegalNotice />
        </Flex>
      </Card>
    </main>
  );
}
