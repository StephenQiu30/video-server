'use client';

import { DownloadSimple, ShieldCheck } from '@phosphor-icons/react';

import FormatPicker from '@/components/format-picker';
import MediaCover from '@/components/media-cover';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
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
      className="grid border-y lg:grid-cols-[5fr_7fr]"
    >
      <div className="min-w-0 py-7 lg:pr-8">
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">
          Available formats
        </p>
        <h2 className="mt-3 text-xl font-medium">选择下载格式</h2>
        <p className="mb-5 mt-2 text-sm leading-6 text-muted-foreground">
          比较清晰度与编码，选择适合设备的版本。
        </p>
        <FormatPicker
          formats={inspection.formats}
          onChange={onChange}
          selectedId={selectedId}
        />
        <Button
          className="mt-5 h-12 w-full text-[15px]"
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

      <div className="min-w-0 border-t py-7 lg:border-t-0 lg:border-l lg:pl-8">
        <MediaCover
          alt={`${inspection.title} 视频封面`}
          duration={formatDuration(inspection.duration_seconds)}
          platform={inspection.extractor_key}
          priority
          src={inspection.thumbnail_url}
        />
        <h2 className="mt-5 text-xl font-medium leading-8 tracking-[-0.015em]">
          {inspection.title}
        </h2>
        <Separator className="my-4" />
        <dl className="flex flex-wrap items-center gap-x-5 gap-y-3 text-sm text-muted-foreground">
          <div>
            <dt className="sr-only">平台</dt>
            <dd>
              <Badge variant="neutral">{inspection.extractor_key}</Badge>
            </dd>
          </div>
          <div>
            <dt className="sr-only">时长</dt>
            <dd className="font-mono">
              {formatDuration(inspection.duration_seconds)}
            </dd>
          </div>
          <div className="min-w-0">
            <dt className="sr-only">媒体 ID</dt>
            <dd className="break-all font-mono text-xs">
              {inspection.provider_media_id}
            </dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
