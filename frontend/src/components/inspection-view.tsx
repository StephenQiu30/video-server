'use client';

import {
  CheckCircleFilled,
  CopyOutlined,
  DownloadOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import { Button, Divider, Flex, Space, Tag, Typography } from 'antd';
import { useState } from 'react';

import FormatPicker from '@/components/format-picker';
import MediaCover from '@/components/media-cover';
import type { Inspection } from '@/types/video';
import { formatDuration } from '@/utils/format';

type InspectionViewProps = {
  busy: boolean;
  inspection: Inspection;
  onChange: (id: string) => void;
  onCreate: () => void;
  selectedId: string;
};

export default function InspectionView({
  busy,
  inspection,
  onChange,
  onCreate,
  selectedId,
}: InspectionViewProps) {
  const [copied, setCopied] = useState(false);

  async function copyInfo() {
    if (!navigator.clipboard) return;
    const text = `${inspection.title}\n${inspection.extractor_key}\n${inspection.provider_media_id}`;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <ProCard title="解析结果">
      <section aria-labelledby="inspection-title">
        <div className="inspection-grid">
          <div>
            <MediaCover
              alt={`${inspection.title} 视频封面`}
              duration={formatDuration(inspection.duration_seconds)}
              platform={inspection.extractor_key}
              src={inspection.thumbnail_url}
            />
          </div>

          <div className="inspection-detail-panel">
            <Typography.Title id="inspection-title" level={3}>
              {inspection.title}
            </Typography.Title>
            <Space
              className="inspection-meta"
              size={8}
              split={<Divider type="vertical" />}
              wrap
            >
              <span>{inspection.extractor_key}</span>
              <span>{formatDuration(inspection.duration_seconds)}</span>
              <span>媒体 ID：{inspection.provider_media_id}</span>
            </Space>

            <Divider />

            <div className="format-heading">
              <Typography.Text strong>选择下载格式</Typography.Text>
              <Tag>{inspection.formats.length} 个版本</Tag>
            </div>
            <FormatPicker
              formats={inspection.formats}
              onChange={onChange}
              selectedId={selectedId}
            />

            <Button
              block
              className="create-download-button"
              disabled={!selectedId}
              icon={<DownloadOutlined aria-hidden />}
              loading={busy}
              onClick={onCreate}
              type="primary"
            >
              {busy ? '正在创建任务…' : '开始下载'}
            </Button>
          </div>
        </div>

        <Divider />
        <Flex
          className="inspection-footer"
          gap="middle"
          justify="space-between"
          wrap
        >
          <Button
            icon={
              copied ? (
                <CheckCircleFilled aria-hidden />
              ) : (
                <CopyOutlined aria-hidden />
              )
            }
            onClick={() => void copyInfo()}
          >
            {copied ? '已复制视频信息' : '复制视频信息'}
          </Button>
          <Typography.Text type="secondary">
            <SafetyCertificateOutlined /> 仅下载你有权处理的公开内容；不支持
            Cookie、DRM、私有内容与直播播放列表。
          </Typography.Text>
          <span aria-live="polite" hidden>
            {copied ? '视频信息已复制到剪贴板' : ''}
          </span>
        </Flex>
      </section>
    </ProCard>
  );
}
