import Alert from 'antd/es/alert';
import Button from 'antd/es/button';
import Card from 'antd/es/card';
import Spin from 'antd/es/spin';
import Tag from 'antd/es/tag';
import Typography from 'antd/es/typography';
import { type FormEvent, type RefObject, useRef, useState } from 'react';
import {
  createDownload,
  createIdempotencyKey,
  displayError,
  inspectMedia,
} from '@/features/download/api';
import FormatPicker from '@/features/download/FormatPicker';
import { navigate } from '@/features/download/navigation';
import type { Inspection } from '@/features/download/types';
import { validateMediaUrl } from '@/features/download/validation';

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
    if (!inspection || !selectedId) {
      return;
    }
    setBusy('create');
    setError(null);
    try {
      const payload = `${inspection.id}:${selectedId}`;
      const result = await createDownload(
        inspection.id,
        selectedId,
        keyFor(downloadKey, payload),
      );
      navigate(`/downloads/${result.id}`);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <Tag color="purple">安全的公开内容下载</Tag>
        <Typography.Title level={1}>万能视频下载与智能分析</Typography.Title>
        <Typography.Paragraph className={styles.lead}>
          粘贴公开视频地址，先查看真实可用的清晰度，再创建可追踪、可取消的下载任务。
        </Typography.Paragraph>
      </section>

      <Alert
        className={styles.legal}
        title="仅处理你有权下载的公开内容"
        description="不支持 Cookie、DRM、私有内容、直播或播放列表，也不会协助规避平台访问控制。"
        showIcon
        type="warning"
      />

      <Card className={styles.workspace} variant="borderless">
        <form className={styles.form} onSubmit={handleInspect}>
          <label htmlFor="media-url">公开视频地址</label>
          <div className={styles.inputRow}>
            <input
              autoComplete="url"
              id="media-url"
              maxLength={4096}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://media.example/video"
              type="url"
              value={url}
            />
            <Button
              aria-label="解析视频"
              htmlType="submit"
              loading={busy === 'inspect'}
              size="large"
              type="primary"
            >
              解析视频
            </Button>
          </div>
        </form>

        {error ? (
          <Alert
            className={styles.feedback}
            showIcon
            title={error}
            type="error"
          />
        ) : null}

        {busy === 'inspect' && !inspection ? (
          <div className={styles.loading} aria-live="polite">
            <Spin /> 正在安全解析视频…
          </div>
        ) : null}

        {inspection ? (
          <section className={styles.result} aria-live="polite">
            <div>
              <Typography.Title level={3}>{inspection.title}</Typography.Title>
              <Typography.Text type="secondary">
                时长 {Math.ceil(inspection.duration_seconds / 60)} 分钟 · 来源{' '}
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
        ) : (
          <p className={styles.empty}>解析后将在这里显示可下载格式。</p>
        )}
      </Card>
    </main>
  );
}
