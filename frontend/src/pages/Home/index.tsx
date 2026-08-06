import { LinkOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { Alert, Button, Col, Grid, Input, Row, Spin, Typography } from 'antd';
import { type FormEvent, type RefObject, useRef, useState } from 'react';

import stageCover from '@/assets/product-launch-stage.webp';
import FormatPicker from '@/components/FormatPicker';
import {
  createDownload,
  createIdempotencyKey,
  displayError,
  inspectMedia,
} from '@/services/download';
import type { Inspection } from '@/types/video';
import { formatDuration } from '@/utils/format';
import { validateMediaUrl } from '@/utils/validation';

import styles from './index.module.css';

type BusyAction = 'inspect' | 'create' | null;
type StableKey = { payload: string; value: string };

function keyFor(ref: RefObject<StableKey | null>, payload: string): string {
  if (ref.current?.payload !== payload) {
    ref.current = { payload, value: createIdempotencyKey() };
  }
  return ref.current.value;
}

export default function HomePage() {
  const screens = Grid.useBreakpoint();
  const [url, setUrl] = useState('');
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [selectedId, setSelectedId] = useState('');
  const [busy, setBusy] = useState<BusyAction>(null);
  const [error, setError] = useState<string | null>(null);
  const inspectionKey = useRef<StableKey | null>(null);
  const downloadKey = useRef<StableKey | null>(null);

  async function handleInspect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = url.trim();
    const validation = validateMediaUrl(normalized);
    if (validation) {
      setError(validation);
      return;
    }
    setBusy('inspect');
    setError(null);
    try {
      const result = await inspectMedia(
        normalized,
        keyFor(inspectionKey, normalized),
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
        keyFor(downloadKey, payload),
      );
      history.push(`/downloads/${result.id}`);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setBusy(null);
    }
  }

  return (
    <PageContainer ghost title={false}>
      <main
        className={styles.page}
        style={{ padding: screens.md ? '88px 24px 56px' : '48px 14px 40px' }}
      >
        <section className={styles.hero}>
          <Typography.Title level={1}>万能视频下载与智能分析</Typography.Title>
          <Typography.Paragraph>
            输入公开视频地址，选择清晰度下载，并用 AI 提取摘要、观点与思维导图。
          </Typography.Paragraph>
          <form className={styles.search} onSubmit={handleInspect}>
            <label className={styles.label} htmlFor="media-url">
              公开视频地址
            </label>
            <Row gutter={[10, 10]}>
              <Col xs={24} sm={18}>
                <Input
                  autoComplete="url"
                  id="media-url"
                  maxLength={4096}
                  onChange={(event) => setUrl(event.target.value)}
                  placeholder="粘贴 YouTube、Bilibili 等公开视频地址"
                  prefix={<LinkOutlined />}
                  size="large"
                  type="url"
                  value={url}
                />
              </Col>
              <Col xs={24} sm={6}>
                <Button
                  aria-label="解析视频"
                  block={!screens.sm}
                  htmlType="submit"
                  loading={busy === 'inspect'}
                  size="large"
                  type="primary"
                >
                  解析视频
                </Button>
              </Col>
            </Row>
          </form>
        </section>

        {error ? <Alert showIcon title={error} type="error" /> : null}
        {busy === 'inspect' && !inspection ? (
          <div aria-live="polite" className={styles.loading}>
            <Spin /> 正在安全解析视频…
          </div>
        ) : null}

        {inspection ? (
          <ProCard
            className={styles.preview}
            styles={{ body: { padding: 0 } }}
            variant="outlined"
          >
            <Row align="stretch">
              <Col xs={24} md={10}>
                <img
                  alt="视频预览封面"
                  src={stageCover}
                  style={{ aspectRatio: screens.md ? undefined : '16 / 9' }}
                />
              </Col>
              <Col xs={24} md={14}>
                <section
                  className={styles.previewBody}
                  style={{ padding: screens.md ? 32 : 24 }}
                >
                  <div>
                    <Typography.Title level={2}>
                      {inspection.title}
                    </Typography.Title>
                    <Typography.Text type="secondary">
                      {formatDuration(inspection.duration_seconds)} · 来源{' '}
                      {inspection.extractor_key}
                    </Typography.Text>
                  </div>
                  <FormatPicker
                    formats={inspection.formats}
                    onChange={setSelectedId}
                    selectedId={selectedId}
                  />
                  <Button
                    aria-label="开始下载"
                    disabled={!selectedId}
                    loading={busy === 'create'}
                    onClick={handleCreate}
                    size="large"
                    type="primary"
                  >
                    开始下载
                  </Button>
                </section>
              </Col>
            </Row>
          </ProCard>
        ) : null}

        <Alert
          className={styles.legal}
          description="不支持 Cookie、DRM、私有内容、直播或播放列表，也不会协助规避平台访问控制。"
          icon={<SafetyCertificateOutlined />}
          showIcon
          title="仅处理你有权下载的公开内容"
          type="info"
        />
      </main>
    </PageContainer>
  );
}
