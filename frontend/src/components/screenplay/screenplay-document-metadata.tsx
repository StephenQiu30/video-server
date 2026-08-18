import { Warning } from '@phosphor-icons/react';

import {
  documentErrorLabel,
  documentFormatLabels,
  documentStatusLabels,
  formatDocumentDate,
  formatDocumentSize,
  languageLabel,
  qualityWarningLabel,
} from '@/components/screenplay/screenplay-document-format';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import type { ScreenplayDocument } from '@/types/video';

export function ScreenplayDocumentMetadata({
  document,
}: {
  document: ScreenplayDocument;
}) {
  const fields = [
    ['格式', documentFormatLabels[document.source_format]],
    ['语言', languageLabel(document.detected_language)],
    ['场景', countLabel(document.scene_count, '个')],
    ['字符', countLabel(document.character_count, '个')],
    ['文件大小', formatDocumentSize(document.declared_size_bytes)],
    ['导入状态', documentStatusLabels[document.status]],
    ['创建时间', formatDocumentDate(document.created_at)],
    ['存储策略', '持久保存'],
  ];
  const error = documentErrorLabel(document);

  return (
    <section
      aria-labelledby="document-metadata-title"
      className="mt-8 border-y border-border/70 py-5 sm:mt-10 sm:py-6"
    >
      <div className="flex items-baseline justify-between gap-4">
        <h2
          className="text-lg font-medium tracking-[-0.02em]"
          id="document-metadata-title"
        >
          文档信息
        </h2>
        <span className="text-xs text-muted-foreground">导入摘要</span>
      </div>
      <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-5 text-sm sm:grid-cols-4 lg:grid-cols-8">
        {fields.map(([label, value]) => (
          <div className="min-w-0" key={label}>
            <dt className="text-xs text-muted-foreground">{label}</dt>
            <dd className="mt-1 truncate tabular-nums" title={value}>
              {value}
            </dd>
          </div>
        ))}
      </dl>
      {error ? (
        <Alert className="mt-6" variant="destructive">
          <AlertTitle>解析未完成</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      {document.quality_warnings.length ? (
        <Alert className="mt-6" variant="warning">
          <Warning aria-hidden />
          <div className="min-w-0">
            <AlertTitle>需要人工核对</AlertTitle>
            <AlertDescription>
              <ul className="mt-1 list-disc space-y-1 pl-4">
                {document.quality_warnings.map((warning) => (
                  <li key={warning}>{qualityWarningLabel(warning)}</li>
                ))}
              </ul>
            </AlertDescription>
          </div>
        </Alert>
      ) : null}
    </section>
  );
}

function countLabel(value: number | null, suffix: string) {
  return value === null
    ? '等待解析'
    : `${value.toLocaleString('zh-CN')} ${suffix}`;
}
