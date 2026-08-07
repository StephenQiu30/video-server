import { LinkOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { Alert, Button, Input, Space, Spin, Typography } from 'antd';
import { type FormEvent, type RefObject, useRef, useState } from 'react';

import {
  createDownload,
  createIdempotencyKey,
  displayError,
  inspectMedia,
} from '@/services/download';
import type { Inspection } from '@/types/video';
import { validateMediaUrl } from '@/utils/validation';

import InspectionResult from './components/InspectionResult';
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
    <PageContainer className={styles.container} ghost title={false}>
      <main className={styles.page}>
        <section className={styles.hero}>
          <Typography.Title level={1}>
            解析并下载视频，获取 AI 智能分析
          </Typography.Title>
          <Typography.Paragraph>
            支持 YouTube、Bilibili、抖音、TikTok、Vimeo 等主流公开视频平台
          </Typography.Paragraph>
          <form className={styles.search} onSubmit={handleInspect}>
            <label className={styles.label} htmlFor="media-url">
              公开视频地址
            </label>
            <Space.Compact block>
              <Input
                autoComplete="url"
                id="media-url"
                maxLength={4096}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="请输入视频链接（支持 Bilibili、YouTube、抖音分享链接）"
                prefix={<LinkOutlined />}
                size="large"
                type="url"
                value={url}
              />
              <Button
                aria-label="解析视频"
                className={styles.inspect}
                htmlType="submit"
                loading={busy === 'inspect'}
                size="large"
                type="primary"
              >
                解析视频
              </Button>
            </Space.Compact>
          </form>
        </section>

        {error ? (
          <Alert
            className={styles.feedback}
            showIcon
            title={error}
            type="error"
          />
        ) : null}
        {busy === 'inspect' && !inspection ? (
          <div aria-live="polite" className={styles.loading}>
            <Spin /> 正在安全解析视频…
          </div>
        ) : null}

        {inspection ? (
          <InspectionResult
            busy={busy === 'create'}
            inspection={inspection}
            onChange={setSelectedId}
            onCreate={handleCreate}
            selectedId={selectedId}
          />
        ) : null}
      </main>
    </PageContainer>
  );
}
