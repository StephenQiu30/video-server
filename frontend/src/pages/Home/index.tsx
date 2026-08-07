import { LinkOutlined } from '@ant-design/icons';
import {
  PageContainer,
  ProForm,
  ProFormText,
} from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { Alert, Button, Col, Flex, Form, Row, Spin } from 'antd';
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
      content="粘贴公开视频链接，解析后选择格式并创建下载任务。"
      ghost
      title="新建下载"
    >
      <Flex gap={16} vertical style={{ marginTop: inspection ? 0 : 56 }}>
        <ProForm<InspectForm> onFinish={handleInspect} submitter={false}>
          <Row align="bottom" gutter={16}>
            <Col sm={20} xs={24}>
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
            </Col>
            <Col sm={4} xs={24}>
              <Form.Item label=" ">
                <Button
                  aria-label="解析视频"
                  block
                  htmlType="submit"
                  loading={busy === 'inspect'}
                  size="large"
                  type="primary"
                >
                  解析视频
                </Button>
              </Form.Item>
            </Col>
          </Row>
        </ProForm>

        {error ? <Alert showIcon title={error} type="info" /> : null}
        {busy === 'inspect' && !inspection ? (
          <Flex align="center" aria-live="polite" gap={8}>
            <Spin size="small" /> 正在解析视频信息…
          </Flex>
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
      </Flex>
    </PageContainer>
  );
}
