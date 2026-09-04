'use client';

import { DownloadSimple, UploadSimple } from '@phosphor-icons/react';

import FormatPicker from '@/components/intake/format-picker';
import MediaCover from '@/components/intake/media-cover';
import { Button } from '@/components/ui/button';
import type { Inspection } from '@/types/video';
import { formatDuration } from '@/utils/format';

type InspectionWorkspaceProps = {
  busy: boolean;
  inspection: Inspection;
  onChange: (id: string) => void;
  onCreate: () => void;
  onUseUpload: () => void;
  selectedId: string;
};

export default function InspectionWorkspace({
  busy,
  inspection,
  onChange,
  onCreate,
  onUseUpload,
  selectedId,
}: InspectionWorkspaceProps) {
  const selected = inspection.formats.find((item) => item.id === selectedId);
  const downloadable = inspection.access_decision === 'downloadable';
  const gallery = inspection.media_kind === 'image_gallery';
  const collection = inspection.media_kind === 'video_collection';

  return (
    <section
      aria-label="解析结果"
      className="grid gap-10 pt-10 lg:grid-cols-[minmax(0,1.55fr)_minmax(360px,1fr)] lg:gap-14"
    >
      <div className="min-w-0">
        <MediaCover
          alt={`${inspection.title} 媒体封面`}
          fallback={{
            detail: inspectionDetailLabel(
              inspection,
              selected?.plan ?? undefined,
            ),
            eyebrow: inspection.extractor_key,
            title: inspection.title,
          }}
          priority
          src={inspection.thumbnail_url}
        />
        <h2 className="mt-5 text-xl font-medium leading-8 tracking-[-0.025em] sm:text-2xl">
          {inspection.title}
        </h2>
        <dl className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-muted-foreground tabular-nums">
          <Meta label="平台" mono value={inspection.extractor_key} />
          {inspection.duration_seconds > 0 ? (
            <Meta
              label="时长"
              value={formatDuration(inspection.duration_seconds)}
            />
          ) : null}
          {gallery ? (
            <Meta
              label="媒体"
              value={`图文作品 · ${inspection.asset_count} 张原图`}
            />
          ) : collection ? (
            <Meta
              label="媒体"
              value={`视频合集 · ${inspection.asset_count} 个视频`}
            />
          ) : selected?.plan ? (
            <Meta
              label="当前清晰度"
              value={`${selected.plan.width}×${selected.plan.height}`}
            />
          ) : null}
        </dl>
      </div>

      <div className="min-w-0">
        <h2 className="text-base font-medium">
          {downloadable
            ? gallery || collection
              ? '下载内容'
              : '画质预设'
            : decisionTitle(inspection.access_decision)}
        </h2>
        {downloadable ? (
          <FormatPicker
            formats={inspection.formats}
            mediaKind={inspection.media_kind}
            onChange={onChange}
            selectedId={selectedId}
          />
        ) : (
          <div aria-live="polite" className="py-6">
            <p className="text-sm leading-6 text-muted-foreground">
              {inspection.user_action ?? '当前来源不能创建下载任务。'}
            </p>
          </div>
        )}
        {selected?.plan ? (
          <dl className="mt-7 grid grid-cols-2 gap-x-5 gap-y-4 pt-5 text-sm">
            <SelectionMeta
              label="容器"
              value={selected.plan.container_preference.toUpperCase()}
            />
            <SelectionMeta
              label="兼容策略"
              value={compatibilityLabel(selected.plan.compatibility_profile)}
            />
            <SelectionMeta
              label="视频编码"
              value={selected.plan.video_codec_family.toUpperCase()}
            />
            <SelectionMeta
              label="音频编码"
              value={selected.plan.audio_codec_family.toUpperCase()}
            />
          </dl>
        ) : (gallery || collection) && selected ? (
          <dl className="mt-7 grid grid-cols-2 gap-x-5 gap-y-4 pt-5 text-sm">
            <SelectionMeta
              label="媒体类型"
              value={collection ? '视频合集' : '官方图文'}
            />
            <SelectionMeta
              label="内容数量"
              value={`${inspection.asset_count} ${collection ? '个视频' : '张原图'}`}
            />
            <SelectionMeta label="导出格式" value="ZIP" />
            <SelectionMeta
              label="下载方式"
              value={collection ? '视频打包' : '原图打包'}
            />
          </dl>
        ) : null}
        {inspection.access_decision === 'export_required' ? (
          <Button
            className="mt-7 h-13 w-full text-[15px]"
            onClick={onUseUpload}
          >
            <UploadSimple size={19} />
            上传自有 MP4
          </Button>
        ) : downloadable ? (
          <Button
            className="mt-7 h-13 w-full text-[15px]"
            disabled={!selectedId || busy}
            onClick={onCreate}
          >
            <DownloadSimple size={19} />
            {busy ? '正在创建任务…' : '创建下载任务'}
          </Button>
        ) : null}
      </div>
    </section>
  );
}

function decisionTitle(decision: Inspection['access_decision']) {
  if (decision === 'playback_only') return '仅支持官方播放';
  if (decision === 'export_required') return '需要导入自有文件';
  if (decision === 'blocked') return '当前不可下载';
  return '当前来源不可下载';
}

function Meta({
  label,
  mono = false,
  value,
}: {
  label: string;
  mono?: boolean;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3 before:content-['·'] first:before:hidden">
      <dt className="sr-only">{label}</dt>
      <dd className={mono ? 'font-mono' : 'tabular-nums'}>{value}</dd>
    </div>
  );
}

function inspectionDetailLabel(
  inspection: Inspection,
  selected: Inspection['formats'][number]['plan'] | undefined,
) {
  if (inspection.media_kind === 'image_gallery') {
    return `${inspection.asset_count} 张原图 · ZIP`;
  }
  if (inspection.media_kind === 'video_collection') {
    return `${inspection.asset_count} 个视频 · ZIP`;
  }
  if (selected) {
    return `${selected.width}×${selected.height}`;
  }
  return '封面未提供';
}

function SelectionMeta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 font-medium">{value}</dd>
    </div>
  );
}

function compatibilityLabel(value: string) {
  if (value === 'quality') return '画质优先';
  if (value === 'smallest') return '体积优先';
  return '均衡';
}
