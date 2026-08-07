import { LinkOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { Alert, Button, Input, Spin, Typography } from 'antd';
import { type FormEvent, type RefObject, useRef, useState } from 'react';

import {
  createDownload,
  createIdempotencyKey,
  displayError,
  inspectMedia,
} from '@/services/download';
import type { Inspection } from '@/types/video';
import { normalizeMediaUrl, URL_MESSAGE } from '@/utils/validation';

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
    const normalized = normalizeMediaUrl(url);
    if (!normalized) {
      setInspection(null);
      setSelectedId('');
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
        <header className={styles.intro}>
          <Typography.Title level={1}>下载视频，继续分析</Typography.Title>
          <Typography.Paragraph>
            粘贴公开视频链接，选择需要的清晰度并创建下载任务。完成后可继续生成摘要、观点和思维导图。
          </Typography.Paragraph>
        </header>

        <ProCard className={styles.commandCard} variant="outlined">
          <form className={styles.command} onSubmit={handleInspect}>
            <div className={styles.field}>
              <label htmlFor="media-url">公开视频地址</label>
              <Input
                aria-label="公开视频地址"
                autoComplete="off"
                id="media-url"
                maxLength={4096}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="粘贴视频链接或分享文案"
                prefix={<LinkOutlined />}
                size="large"
                type="text"
                value={url}
              />
            </div>
            <Button
              aria-label="解析视频"
              htmlType="submit"
              loading={busy === 'inspect'}
              size="large"
              type="primary"
            >
              解析视频
            </Button>
          </form>
          <div className={styles.note}>
            <SafetyCertificateOutlined aria-hidden />
            <Typography.Text type="secondary">
              支持常见视频平台和标准 HTTP(S) 公开视频地址
            </Typography.Text>
          </div>
        </ProCard>

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
            <Spin size="small" /> 正在解析视频信息…
          </div>
        ) : null}
        {inspection ? (
          <ProCard
            className={styles.resultShell}
            styles={{ body: { padding: 0 } }}
            variant="outlined"
          >
            <InspectionResult
              busy={busy === 'create'}
              inspection={inspection}
              onChange={setSelectedId}
              onCreate={handleCreate}
              selectedId={selectedId}
            />
          </ProCard>
        ) : null}
      </main>
    </PageContainer>
  );
}
