import {
  AppstoreOutlined,
  ArrowRightOutlined,
  BulbOutlined,
  CheckCircleFilled,
  ClockCircleOutlined,
  FileTextOutlined,
  GlobalOutlined,
  LinkOutlined,
  NodeIndexOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import {
  PageContainer,
  ProCard,
} from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { Alert, Button, Input, Spin, Steps, Tag, Typography } from 'antd';
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

const supportedPlatforms = [
  { icon: <GlobalOutlined />, label: 'YouTube' },
  { icon: <AppstoreOutlined />, label: 'Bilibili' },
  { icon: <FileTextOutlined />, label: '抖音' },
  { icon: <BulbOutlined />, label: '视频号' },
  { icon: <NodeIndexOutlined />, label: '小红书' },
  { icon: <ArrowRightOutlined />, label: '更多 1000+' },
];

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
        <section className={styles.hero}>
          <Typography.Text className={styles.eyebrow}>
            VIDEO WORKSPACE
          </Typography.Text>
          <Typography.Title
            aria-label="解析并下载视频，获取 AI 智能分析"
            level={1}
          >
            把视频变成可执行的知识
          </Typography.Title>
          <Typography.Paragraph className={styles.heroCopy}>
            支持 1000+ 平台视频解析下载，并通过 AI 快速提炼洞见、总结要点、生成行动项。
          </Typography.Paragraph>
          <form className={styles.search} onSubmit={handleInspect}>
            <div className={styles.searchField}>
              <label className={styles.label} htmlFor="media-url">
                公开视频地址
              </label>
              <Input
                aria-label="公开视频地址"
                autoComplete="off"
                id="media-url"
                maxLength={4096}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="粘贴视频链接，支持 YouTube、Bilibili、抖音、视频号等"
                prefix={<LinkOutlined />}
                size="large"
                type="text"
                value={url}
              />
            </div>
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
          </form>
          <section aria-label="下载流程" className={styles.flowRail}>
            <Steps
              current={inspection ? 1 : 0}
              items={[
                { title: '解析' },
                { title: '下载' },
                { title: '分析' },
              ]}
              size="small"
            />
          </section>
          <div className={styles.platforms}>
            <span className={styles.platformLabel}>支持的平台</span>
            {supportedPlatforms.map((platform) => (
              <Tag className={styles.platformTag} key={platform.label}>
                {platform.icon}
                {platform.label}
              </Tag>
            ))}
          </div>
          <div className={styles.trustRow}>
            <span>
              <SafetyCertificateOutlined /> 公开链接安全解析
            </span>
            <span>
              <CheckCircleFilled /> 不保存你的源视频地址
            </span>
            <span>
              <ClockCircleOutlined /> 任务状态实时更新
            </span>
          </div>
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
          <ProCard
            className={styles.resultShell}
            ghost
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
