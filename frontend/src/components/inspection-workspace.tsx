'use client';

import { DownloadSimple, ShieldCheck } from '@phosphor-icons/react';

import FormatPicker from '@/components/format-picker';
import MediaCover from '@/components/media-cover';
import { Button } from '@/components/ui/button';
import type { Inspection } from '@/types/video';
import { formatDuration } from '@/utils/format';

type InspectionWorkspaceProps = {
  busy: boolean;
  inspection: Inspection;
  onChange: (id: string) => void;
  onCreate: () => void;
  selectedId: string;
};

export default function InspectionWorkspace({
  busy,
  inspection,
  onChange,
  onCreate,
  selectedId,
}: InspectionWorkspaceProps) {
  return (
    <section
      aria-label="解析结果"
      className="grid gap-10 lg:grid-cols-[minmax(0,0.94fr)_minmax(0,1.06fr)] lg:gap-11"
    >
      <div className="min-w-0">
        <div className="mb-3 flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold">选择下载格式</h2>
        </div>
        <FormatPicker
          formats={inspection.formats}
          onChange={onChange}
          selectedId={selectedId}
        />
        <Button
          className="mt-5 h-14 w-full text-base"
          disabled={!selectedId || busy}
          onClick={onCreate}
        >
          <DownloadSimple size={19} />
          {busy ? '正在创建任务…' : '开始下载'}
        </Button>
        <p className="mt-5 flex items-start gap-2 text-xs leading-5 text-muted-foreground">
          <ShieldCheck className="mt-0.5 size-4 shrink-0" />
          仅支持你有权处理的公开、非 DRM
          视频；请遵守平台服务条款及相关法律法规。
        </p>
      </div>

      <div className="min-w-0">
        <MediaCover
          alt={`${inspection.title} 视频封面`}
          duration={formatDuration(inspection.duration_seconds)}
          platform={inspection.extractor_key}
          priority
          src={inspection.thumbnail_url}
        />
        <h2 className="mt-5 text-xl font-semibold leading-8 tracking-[-0.015em]">
          {inspection.title}
        </h2>
        <p className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-sm text-muted-foreground">
          <span className="font-medium text-[#e94776]">
            {inspection.extractor_key}
          </span>
          <span>{formatDuration(inspection.duration_seconds)}</span>
          <span>媒体 ID：{inspection.provider_media_id}</span>
        </p>
      </div>
    </section>
  );
}
