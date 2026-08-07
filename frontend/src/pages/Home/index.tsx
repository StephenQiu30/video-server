import { LinkOutlined } from '@ant-design/icons';
import {
  PageContainer,
  ProCard,
  ProForm,
  ProFormText,
} from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { Alert, Button, Spin } from 'antd';
import { type RefObject, useRef, useState } from 'react';

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
type InspectForm = { url?: string };

function keyFor(ref: RefObject<StableKey | null>, payload: string): string {
  if (ref.current?.payload !== payload) {
    ref.current = { payload, value: createIdempotencyKey() };
  }
  return ref.current.value;
}

export default function HomePage() {
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [selectedId, setSelectedId] = useState('');
  const [busy, setBusy] = useState<BusyAction>(null);
  const [error, setError] = useState<string | null>(null);
  const inspectionKey = useRef<StableKey | null>(null);
  const downloadKey = useRef<StableKey | null>(null);

  async function handleInspect(values: InspectForm) {
    const normalized = normalizeMediaUrl(values.url ?? '');
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
    <PageContainer
      className={styles.container}
      content="粘贴公开视频链接，解析后选择格式并创建下载任务。"
      title="新建下载"
    >
      <main className={inspection ? styles.page : styles.emptyPage}>
        <ProCard className={styles.commandCard} variant="outlined">
          <ProForm<InspectForm>
            className={styles.command}
            onFinish={handleInspect}
            submitter={false}
          >
            <ProFormText
              fieldProps={{
                'aria-label': '公开视频地址',
                autoComplete: 'off',
                id: 'media-url',
                maxLength: 4096,
                prefix: <LinkOutlined />,
                size: 'large',
              }}
              label="公开视频地址"
              name="url"
              placeholder="粘贴视频链接或分享文案"
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
          </ProForm>
        </ProCard>

        {error ? (
          <Alert
            className={styles.feedback}
            showIcon
            title={error}
            type="info"
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
