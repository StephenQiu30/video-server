'use client';

import { FileText, FileVideo, LinkSimple } from '@phosphor-icons/react';
import type { ReactNode } from 'react';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export type IntakeMode = 'link' | 'video' | 'screenplay';

export function ContentIntakeHero({
  disabled,
  linkForm,
  mode,
  onModeChange,
  screenplayForm,
  videoForm,
}: {
  disabled: boolean;
  linkForm: ReactNode;
  mode: IntakeMode;
  onModeChange: (mode: IntakeMode) => void;
  screenplayForm: ReactNode;
  videoForm: ReactNode;
}) {
  return (
    <section className="pt-10 sm:pt-12 lg:pt-14">
      <h1 className="editorial-title sm:whitespace-nowrap">
        把素材，
        <span className="block sm:ml-[0.85em] sm:inline">带回本地。</span>
      </h1>
      <p className="mt-5 max-w-2xl text-[15px] leading-7 text-muted-foreground">
        解析公开视频链接，或上传本地视频与剧本文档。
      </p>

      <Tabs
        className="mt-7 gap-0"
        onValueChange={(value) => onModeChange(value as IntakeMode)}
        value={mode}
      >
        <TabsList
          aria-label="选择内容来源"
          className="grid h-11 w-full grid-cols-3 gap-0 p-0 sm:inline-flex sm:w-fit sm:gap-6 sm:p-[3px]"
          variant="line"
        >
          <TabsTrigger
            className="min-w-0 px-1 sm:px-2"
            disabled={disabled}
            value="link"
          >
            <LinkSimple aria-hidden />
            链接解析
          </TabsTrigger>
          <TabsTrigger
            className="min-w-0 px-1 sm:px-2"
            disabled={disabled}
            value="video"
          >
            <FileVideo aria-hidden />
            本地视频
          </TabsTrigger>
          <TabsTrigger
            className="min-w-0 px-1 sm:px-2"
            disabled={disabled}
            value="screenplay"
          >
            <FileText aria-hidden />
            剧本文档
          </TabsTrigger>
        </TabsList>
        <TabsContent className="pt-4" value="link">
          {linkForm}
        </TabsContent>
        <TabsContent className="pt-4" value="video">
          {videoForm}
        </TabsContent>
        <TabsContent className="pt-4" value="screenplay">
          {screenplayForm}
        </TabsContent>
      </Tabs>
    </section>
  );
}
