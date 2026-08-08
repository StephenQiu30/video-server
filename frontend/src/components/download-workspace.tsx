'use client';

import { LinkOutlined, ReloadOutlined } from '@ant-design/icons';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import { Alert, Button, Empty, Flex, Input, Space, Typography } from 'antd';
import { useRouter } from 'next/navigation';
import { type RefObject, useEffect, useRef, useState } from 'react';

import InspectionView from '@/components/inspection-view';
import {
  createDownload,
  createIdempotencyKey,
  displayError,
  inspectMedia,
} from '@/services/download';
import type { Inspection } from '@/types/video';
import { normalizeMediaUrl, URL_MESSAGE } from '@/utils/validation';

type BusyAction = 'inspect' | 'create' | null;
type StableKey = { payload: string; value: string };

const DESIGN_SOURCE_URL = 'https://www.bilibili.com/video/BV1D6u86fETf/';
const DESIGN_KEY_STORAGE = 'video-server:design-inspection-key';
const sourceExamples = [
  { label: 'Bilibili', url: DESIGN_SOURCE_URL },
  { label: 'YouTube', url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' },
  { label: 'Vimeo', url: 'https://vimeo.com/76979871' },
];

export default function DownloadWorkspace() {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [selectedId, setSelectedId] = useState('');
  const [busy, setBusy] = useState<BusyAction>(null);
  const [error, setError] = useState<string | null>(null);
  const inspectionKey = useRef<StableKey | null>(null);
  const downloadKey = useRef<StableKey | null>(null);

  useEffect(() => {
    const isDesignInspection =
      process.env.NODE_ENV !== 'production' &&
      new URLSearchParams(window.location.search).get('design') ===
        'inspection';
    if (!isDesignInspection) return;

    let active = true;
    const storedKey = window.sessionStorage.getItem(DESIGN_KEY_STORAGE);
    const key = storedKey ?? createIdempotencyKey();
    window.sessionStorage.setItem(DESIGN_KEY_STORAGE, key);
    inspectionKey.current = { payload: DESIGN_SOURCE_URL, value: key };
    setUrl(DESIGN_SOURCE_URL);
    setBusy('inspect');
    setError(null);

    void inspectMedia(DESIGN_SOURCE_URL, key)
      .then((result) => {
        if (!active) return;
        setInspection(result);
        setSelectedId(result.formats[0]?.id ?? '');
      })
      .catch((reason: unknown) => {
        if (active) setError(displayError(reason));
      })
      .finally(() => {
        if (active) setBusy(null);
      });

    return () => {
      active = false;
    };
  }, []);

  async function handleInspect() {
    const normalized = normalizeMediaUrl(url);
    if (!normalized) {
      setError(URL_MESSAGE);
      return;
    }
    setBusy('inspect');
    setError(null);
    setInspection(null);
    setSelectedId('');
    try {
      const result = await inspectMedia(
        normalized,
        stableKey(inspectionKey, normalized),
      );
      setInspection(result);
      setSelectedId(result.formats[0]?.id ?? '');
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setBusy(null);
    }
  }

  async function handleCreate() {
    if (!inspection || !selectedId) return;
    setBusy('create');
    setError(null);
    try {
      const payload = `${inspection.id}:${selectedId}`;
      const result = await createDownload(
        inspection.id,
        selectedId,
        stableKey(downloadKey, payload),
      );
      router.push(`/downloads/?jobId=${encodeURIComponent(result.id)}`);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setBusy(null);
    }
  }

  return (
    <PageContainer
      className="home-page"
      content="粘贴公开视频链接，识别真实封面与可用格式，并创建下载任务。"
      title="公开视频解析与下载"
    >
      <div className="workspace-stack">
        <ProCard title="解析视频">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void handleInspect();
            }}
          >
            <Space.Compact block>
              <Input
                allowClear
                aria-label="公开视频地址"
                maxLength={4096}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="粘贴 Bilibili、YouTube、抖音等公开视频链接"
                prefix={<LinkOutlined aria-hidden />}
                value={url}
              />
              <Button
                aria-label={inspection ? '重新解析' : '解析视频'}
                htmlType="submit"
                icon={inspection ? <ReloadOutlined aria-hidden /> : undefined}
                loading={busy === 'inspect'}
                type="primary"
              >
                {inspection ? '重新解析' : '解析视频'}
              </Button>
            </Space.Compact>
          </form>

          <Flex className="source-examples" gap="small" wrap>
            <Typography.Text type="secondary">
              支持 yt-dlp 可识别的公开来源。示例：
            </Typography.Text>
            {!inspection
              ? sourceExamples.map((example) => (
                  <Button
                    key={example.label}
                    onClick={() => setUrl(example.url)}
                    size="small"
                    type="link"
                  >
                    {example.label}
                  </Button>
                ))
              : null}
          </Flex>
        </ProCard>

        {error ? (
          <Alert
            description={error}
            message="操作未完成"
            showIcon
            type="error"
          />
        ) : null}

        {inspection ? (
          <InspectionView
            busy={busy === 'create'}
            inspection={inspection}
            onChange={setSelectedId}
            onCreate={handleCreate}
            selectedId={selectedId}
          />
        ) : (
          <EmptyResult loading={busy === 'inspect'} />
        )}
      </div>
    </PageContainer>
  );
}

function EmptyResult({ loading }: { loading: boolean }) {
  return (
    <ProCard title="解析结果">
      <Empty
        description={
          <Space direction="vertical" size={4}>
            <Typography.Text strong>
              {loading ? '正在识别视频' : '等待解析公开视频'}
            </Typography.Text>
            <Typography.Text type="secondary">
              {loading
                ? '正在安全识别媒体信息和可用格式，请稍候。'
                : '解析结果将在这里展示真实封面、媒体信息与可下载格式。'}
            </Typography.Text>
          </Space>
        }
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    </ProCard>
  );
}

function stableKey(ref: RefObject<StableKey | null>, payload: string) {
  if (ref.current?.payload !== payload) {
    ref.current = { payload, value: createIdempotencyKey() };
  }
  return ref.current.value;
}
