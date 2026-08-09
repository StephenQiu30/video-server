'use client';

import { Check, Copy } from '@phosphor-icons/react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { EvidenceStatement } from '@/types/video';

export default function EvidenceList({
  className,
  items,
  title,
}: {
  className?: string;
  items: EvidenceStatement[];
  title: string;
}) {
  return (
    <section className={className}>
      <h3 className="text-xl font-medium tracking-[-0.02em]">{title}</h3>
      {items.length ? (
        <ol className="mt-5 divide-y border-y">
          {items.map((item, index) => (
            <Statement
              index={index}
              item={item}
              key={`${item.text}-${item.evidence_segment_ids.join(':')}`}
            />
          ))}
        </ol>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground">暂无内容。</p>
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
    <li className="grid grid-cols-[34px_minmax(0,1fr)_40px] items-start gap-3 py-5">
      <span className="pt-1 font-mono text-xs text-muted-foreground">
        {String(index + 1).padStart(2, '0')}
      </span>
      <span className="text-sm leading-7">{item.text}</span>
      <Button
        aria-label={`复制观点 ${index + 1}`}
        onClick={() => void copy()}
        size="icon"
        variant="ghost"
      >
        {copied ? <Check className={cn('text-success')} /> : <Copy />}
      </Button>
    </li>
  );
}
