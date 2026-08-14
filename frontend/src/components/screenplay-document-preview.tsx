import { Info } from '@phosphor-icons/react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import type { ScreenplayDocument } from '@/types/video';

export function ScreenplayDocumentPreview({
  document,
}: {
  document: ScreenplayDocument;
}) {
  return (
    <section aria-labelledby="screenplay-preview-title" className="min-w-0">
      <div className="flex items-baseline justify-between gap-4">
        <h2
          className="text-lg font-medium tracking-[-0.02em]"
          id="screenplay-preview-title"
        >
          规范化剧本
        </h2>
        {document.preview ? (
          <span className="text-xs text-muted-foreground">纯文本预览</span>
        ) : null}
      </div>
      {document.status === 'ready' && document.preview ? (
        <>
          <pre className="mt-4 max-h-[70vh] min-h-80 overflow-auto whitespace-pre-wrap break-words bg-surface px-5 py-6 font-mono text-[13px] leading-7 text-foreground sm:px-8 sm:py-8 sm:text-sm">
            {document.preview}
          </pre>
          {document.preview_truncated ? (
            <Alert className="mt-4" variant="default">
              <Info aria-hidden />
              <div className="min-w-0">
                <AlertTitle>预览已截断</AlertTitle>
                <AlertDescription>
                  这里只显示文件开头的一段，用于快速核对提取结果。
                </AlertDescription>
              </div>
            </Alert>
          ) : null}
        </>
      ) : (
        <div className="mt-4 border-y border-border/70 py-16 text-sm text-muted-foreground">
          {previewStatusMessage(document.status)}
        </div>
      )}
    </section>
  );
}

function previewStatusMessage(status: ScreenplayDocument['status']) {
  if (status === 'uploading') return '文件上传完成后，这里会显示提取结果。';
  if (status === 'verifying') return '正在解析剧本文本，请稍后刷新。';
  if (status === 'ready') return '文档已解析，但当前没有可显示的预览。';
  if (status === 'failed') return '解析失败，未生成规范化剧本文本。';
  if (status === 'cancelled') return '导入已取消，未生成剧本文本。';
  return '文档已过期，预览不再可用。';
}
