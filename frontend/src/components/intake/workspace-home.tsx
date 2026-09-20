import {
  ClockCounterClockwiseIcon,
  DownloadSimpleIcon,
} from '@phosphor-icons/react';
import Link from 'next/link';

import { EditorialIntro } from '@/components/layout/editorial-intro';
import { Button } from '@/components/ui/button';

export function WorkspaceHome() {
  return (
    <section
      className="inner-page pt-10 sm:pt-12 lg:pt-14"
      data-slot="workspace-home"
    >
      <EditorialIntro
        description="在独立页面解析公开链接或上传本地内容；已经创建的任务可以从下载记录继续处理。"
        eyebrow="工作区"
        title={
          <>
            选择素材，
            <span className="block sm:ml-[0.85em] sm:inline">开始下一步。</span>
          </>
        }
        titleClassName="sm:whitespace-nowrap"
      >
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Button asChild className="min-h-11 px-4" size="lg">
            <Link href="/downloads/new">
              <DownloadSimpleIcon data-icon="inline-start" />
              新建下载
            </Link>
          </Button>
          <Button asChild className="min-h-11 px-4" size="lg" variant="outline">
            <Link href="/history">
              <ClockCounterClockwiseIcon data-icon="inline-start" />
              查看下载记录
            </Link>
          </Button>
        </div>
      </EditorialIntro>

      <div className="mt-20 grid gap-10 sm:grid-cols-3 lg:mt-24">
        <WorkspaceStep
          description="粘贴公开媒体链接或平台分享文案，确认可用格式后创建任务。"
          index="01"
          title="链接解析"
        />
        <WorkspaceStep
          description="导入你拥有使用权的本地视频，在同一工作流中继续处理。"
          index="02"
          title="本地视频"
        />
        <WorkspaceStep
          description="上传剧本文档，进入规范化、分析与处理流程。"
          index="03"
          title="剧本文档"
        />
      </div>
    </section>
  );
}

function WorkspaceStep({
  description,
  index,
  title,
}: {
  description: string;
  index: string;
  title: string;
}) {
  return (
    <section>
      <p className="font-mono text-xs text-muted-foreground">{index}</p>
      <h2 className="mt-3 text-base font-medium">{title}</h2>
      <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
        {description}
      </p>
    </section>
  );
}
