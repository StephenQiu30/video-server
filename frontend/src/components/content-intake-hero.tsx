'use client';

import { LinkSimple, UploadSimple } from '@phosphor-icons/react';
import type { ReactNode } from 'react';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export type IntakeMode = 'link' | 'upload';

export function ContentIntakeHero({
  disabled,
  linkForm,
  mode,
  onModeChange,
  uploadForm,
}: {
  disabled: boolean;
  linkForm: ReactNode;
  mode: IntakeMode;
  onModeChange: (mode: IntakeMode) => void;
  uploadForm: ReactNode;
}) {
  return (
    <section className="pt-10 sm:pt-12 lg:pt-14">
      <h1 className="editorial-title sm:whitespace-nowrap">
        把视频，
        <span className="block sm:ml-[0.85em] sm:inline">带回本地。</span>
      </h1>
      <p className="mt-5 max-w-2xl text-[15px] leading-7 text-muted-foreground">
        解析公开链接，或上传你有权处理的本地 MP4。完成后都可以继续拉片分析。
      </p>

      <Tabs
        className="mt-7 gap-0"
        onValueChange={(value) => onModeChange(value as IntakeMode)}
        value={mode}
      >
        <TabsList
          aria-label="选择视频来源"
          className="h-11 gap-6"
          variant="line"
        >
          <TabsTrigger disabled={disabled} value="link">
            <LinkSimple aria-hidden />
            链接解析
          </TabsTrigger>
          <TabsTrigger disabled={disabled} value="upload">
            <UploadSimple aria-hidden />
            本地上传
          </TabsTrigger>
        </TabsList>
        <TabsContent className="pt-4" value="link">
          {linkForm}
        </TabsContent>
        <TabsContent className="pt-4" value="upload">
          {uploadForm}
        </TabsContent>
      </Tabs>
    </section>
  );
}
