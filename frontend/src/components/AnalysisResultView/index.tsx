'use client';

import { CheckIcon, CopyIcon, InfoIcon } from '@phosphor-icons/react';
import { useState } from 'react';

import MindMapTree from '@/components/MindMapTree';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { AnalysisResult, EvidenceStatement } from '@/types/video';
import { formatMilliseconds } from '@/utils/format';

export default function AnalysisResultView({
  result,
}: {
  result: AnalysisResult;
}) {
  return (
    <section aria-label="AI 分析结果">
      <Tabs defaultValue="summary">
        <TabsList>
          <TabsTrigger value="summary">摘要</TabsTrigger>
          <TabsTrigger value="points">关键观点</TabsTrigger>
          <TabsTrigger value="actions">行动项</TabsTrigger>
          <TabsTrigger value="mind-map">思维导图</TabsTrigger>
        </TabsList>
        <TabsContent className="mt-8 space-y-10" value="summary">
          <section className="max-w-4xl">
            <h3 className="text-xl font-semibold">摘要</h3>
            <p className="mt-4 text-base leading-7">{result.summary.text}</p>
            <p className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
              <InfoIcon /> 所有观点均来自本次视频转录证据
            </p>
          </section>
          <Statements items={result.key_points} title="关键要点" />
          <div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr]">
            <Chapters result={result} />
            <section className="lg:border-l lg:pl-10">
              <h3 className="mb-5 text-xl font-semibold">思维导图预览</h3>
              <MindMapTree root={result.mind_map} />
            </section>
          </div>
        </TabsContent>
        <TabsContent className="mt-8" value="points">
          <Statements items={result.key_points} title="关键观点" />
        </TabsContent>
        <TabsContent className="mt-8" value="actions">
          <Statements items={result.action_items} title="行动建议" />
        </TabsContent>
        <TabsContent className="mt-8" value="mind-map">
          <MindMapTree root={result.mind_map} />
        </TabsContent>
      </Tabs>
    </section>
  );
}

function Statements({
  items,
  title,
}: {
  items: EvidenceStatement[];
  title: string;
}) {
  return (
    <section>
      <h3 className="mb-4 text-xl font-semibold">{title}</h3>
      {items.length ? (
        <ol className="divide-y border-y">
          {items.map((item, index) => (
            <Statement item={item} index={index} key={item.text} />
          ))}
        </ol>
      ) : (
        <p className="text-sm text-muted-foreground">暂无内容。</p>
      )}
    </section>
  );
}

function Statement({
  item,
  index,
}: {
  item: EvidenceStatement;
  index: number;
}) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    await navigator.clipboard?.writeText(item.text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }
  return (
    <li className="grid grid-cols-[42px_1fr_auto] items-center gap-4 py-4">
      <span className="font-mono text-sm text-muted-foreground">
        {String(index + 1).padStart(2, '0')}
      </span>
      <p className="leading-6">{item.text}</p>
      <Button
        aria-label={`复制观点 ${index + 1}`}
        onClick={copy}
        size="icon"
        variant="ghost"
      >
        {copied ? <CheckIcon /> : <CopyIcon />}
      </Button>
    </li>
  );
}

function Chapters({ result }: { result: AnalysisResult }) {
  return (
    <section>
      <h3 className="mb-5 text-xl font-semibold">章节</h3>
      <ol className="space-y-5">
        {result.chapters.map((chapter) => (
          <li
            className="grid grid-cols-[58px_1fr] gap-4"
            key={`${chapter.start_ms}:${chapter.title}`}
          >
            <span className="font-mono text-sm text-brand">
              {formatMilliseconds(chapter.start_ms)}
            </span>
            <div>
              <strong>{chapter.title}</strong>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                {chapter.summary}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
