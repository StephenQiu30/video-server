import {
  DownloadOutlined,
  LinkOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import {
  PageContainer,
  ProForm,
  ProFormText,
} from '@ant-design/pro-components';
import { useNavigate } from '@umijs/max';
import { Alert, Button, Flex, Form, Spin, Tag, Typography } from 'antd';
import { type RefObject, useEffect, useRef, useState } from 'react';

import FormatPicker from '@/components/FormatPicker';
import MediaCover from '@/components/MediaCover';
import {
  createDownload,
  createIdempotencyKey,
  displayError,
  inspectMedia,
} from '@/services/download';
import type { Inspection } from '@/types/video';
import { formatDuration } from '@/utils/format';
import { normalizeMediaUrl, URL_MESSAGE } from '@/utils/validation';
import './index.less';

type BusyAction = 'inspect' | 'create' | null;
type StableKey = { payload: string; value: string };
type InspectionFormValues = { url: string };

const DESIGN_SOURCE_URL = 'https://www.bilibili.com/video/BV1D6u86fETf/';
const DESIGN_KEY_STORAGE = 'video-server:design-inspection-key';

export default function DownloadPage() {
  const navigate = useNavigate();
  const [form] = Form.useForm<InspectionFormValues>();
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
    form.setFieldsValue({ url: DESIGN_SOURCE_URL });
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
  }, [form]);

  async function handleInspect(value: string) {
    const normalized = normalizeMediaUrl(value);
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
      navigate(`/downloads/${encodeURIComponent(result.id)}`);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setBusy(null);
    }
  }

  return (
    <PageContainer className="download-page" title="解析下载">
      <ProForm<InspectionFormValues>
        className="download-form"
        form={form}
        layout="vertical"
        onFinish={async ({ url }) => {
          await handleInspect(url);
          return true;
        }}
        submitter={{
          resetButtonProps: false,
          searchConfig: {
            submitText: inspection ? '重新解析' : '解析视频',
          },
          submitButtonProps: {
            icon: inspection ? <ReloadOutlined aria-hidden /> : undefined,
            loading: busy === 'inspect',
          },
        }}
      >
        <ProFormText
          fieldProps={{
            allowClear: true,
            'aria-label': '公开视频地址',
            maxLength: 4096,
            prefix: <LinkOutlined aria-hidden />,
          }}
          label="公开视频地址"
          name="url"
          placeholder="粘贴 Bilibili、YouTube、抖音等公开视频链接"
          rules={[{ required: true, message: '请输入公开视频链接' }]}
          width="xl"
        />
      </ProForm>

      {error || inspection || busy === 'inspect' ? (
        <div className="content-wrap">
          {error ? (
            <Alert
              className="content-alert"
              description={error}
              title="操作未完成"
              showIcon
              type="error"
            />
          ) : null}

          {inspection ? (
            <section className="inspection-result" aria-label="解析结果">
              <div className="inspection-grid">
                <div className="inspection-media">
                  <MediaCover
                    alt={`${inspection.title} 视频封面`}
                    durationSeconds={inspection.duration_seconds}
                    platform={inspection.extractor_key}
                    src={inspection.thumbnail_url}
                  />
                  <Typography.Title level={3} className="inspection-title">
                    {inspection.title}
                  </Typography.Title>
                  <div className="inspection-meta">
                    <Tag variant="filled">{inspection.extractor_key}</Tag>
                    <Typography.Text type="secondary">
                      {formatDuration(inspection.duration_seconds)} · 媒体 ID：
                      {inspection.provider_media_id}
                    </Typography.Text>
                  </div>
                </div>
                <div className="inspection-formats">
                  <div className="format-heading">
                    <Typography.Text strong>选择下载格式</Typography.Text>
                    <Tag variant="filled">
                      {inspection.formats.length} 个版本
                    </Tag>
                  </div>
                  <FormatPicker
                    formats={inspection.formats}
                    onChange={setSelectedId}
                    selectedId={selectedId}
                  />

                  <Button
                    block
                    className="create-download-button"
                    disabled={!selectedId}
                    icon={<DownloadOutlined aria-hidden />}
                    loading={busy === 'create'}
                    onClick={() => void handleCreate()}
                    size="large"
                    type="primary"
                  >
                    {busy === 'create' ? '正在创建任务…' : '开始下载'}
                  </Button>
                </div>
              </div>
            </section>
          ) : busy === 'inspect' ? (
            <Flex className="inspection-loading" align="center" gap={10}>
              <Spin size="small" />
              <Typography.Text type="secondary">
                正在识别媒体信息和可用格式…
              </Typography.Text>
            </Flex>
          ) : null}
        </div>
      ) : null}
    </PageContainer>
  );
}

function stableKey(ref: RefObject<StableKey | null>, payload: string) {
  if (ref.current?.payload !== payload) {
    ref.current = { payload, value: createIdempotencyKey() };
  }
  return ref.current.value;
}
