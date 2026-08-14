import type { ReactNode } from 'react';

import { Item, ItemGroup } from '@/components/ui/item';
import { TabsTrigger } from '@/components/ui/tabs';
import type { ScreenplayAnalysisResult } from '@/types/video';

type ScreenplayEvidence = ScreenplayAnalysisResult['dialogue_findings'][number];

export function EvidenceList({
  className = '',
  heading,
  items,
}: {
  className?: string;
  heading: string;
  items: ScreenplayEvidence[];
}) {
  return (
    <section className={className}>
      <h3 className="mb-4 text-lg font-medium tracking-[-0.02em]">{heading}</h3>
      {items.length ? (
        <ItemGroup asChild className="hairline gap-0 border-y">
          <ul>
            {items.map((item) => (
              <Item
                asChild
                className="hairline block rounded-none border-0 border-b px-0 py-5 last:border-b-0"
                key={item.id}
              >
                <li>
                  <strong className="font-medium">{item.title}</strong>
                  <p className="mt-2 leading-7 text-muted-foreground">
                    {item.description}
                  </p>
                  <EvidenceIds ids={item.evidence_scene_ids} />
                </li>
              </Item>
            ))}
          </ul>
        </ItemGroup>
      ) : (
        <p className="border-y py-7 text-muted-foreground">
          本项没有独立发现。
        </p>
      )}
    </section>
  );
}

export function EvidenceIds({ ids }: { ids: string[] }) {
  return (
    <p className="mt-3 break-all font-mono text-xs text-muted-foreground">
      证据：{ids.join(' · ')}
    </p>
  );
}

export function Detail({
  children,
  label,
}: {
  children: ReactNode;
  label: string;
}) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="mt-1 leading-6">{children}</dd>
    </div>
  );
}

export function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl tabular-nums sm:text-2xl">{value}</p>
    </div>
  );
}

export function ResultTab({
  children,
  value,
}: {
  children: ReactNode;
  value: string;
}) {
  return (
    <TabsTrigger
      className="rounded-none border-x-0 border-t-0 border-b border-transparent px-0 pt-0 pb-3 data-[state=active]:border-foreground"
      value={value}
    >
      {children}
    </TabsTrigger>
  );
}

export function languageLabel(language: string) {
  if (language === 'zh-CN') return '简体中文';
  if (language === 'en-US') return 'English';
  if (language === 'mixed') return '中英混合';
  return '未知';
}
