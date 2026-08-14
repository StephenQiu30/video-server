import type {
  ScreenplayDocument,
  ScreenplayDocumentFormat,
  ScreenplayDocumentStatus,
} from '@/types/video';

export const documentStatusLabels: Record<ScreenplayDocumentStatus, string> = {
  uploading: '等待上传',
  verifying: '正在解析',
  ready: '可以核对',
  failed: '解析失败',
  cancelled: '已取消',
  expired: '已过期',
};

export const documentFormatLabels: Record<ScreenplayDocumentFormat, string> = {
  docx: 'DOCX',
  pdf: 'PDF',
  txt: '纯文本',
  markdown: 'Markdown',
  fountain: 'Fountain',
};

const errorLabels: Record<API.ImportErrorCode, string> = {
  import_storage_unavailable: '文档存储暂时不可用，请稍后刷新。',
  upload_session_expired: '上传会话已过期。',
  upload_incomplete: '文件没有完整上传。',
  import_size_mismatch: '文件大小与上传声明不一致。',
  import_sha256_mismatch: '文件完整性校验未通过。',
  video_import_invalid: '上传内容不是受支持的视频。',
  document_format_unsupported: '该文档格式不受支持。',
  document_encrypted: '加密或受保护的文档无法解析。',
  document_archive_unsafe: '文档包含不安全的压缩包或外部内容。',
  document_text_unavailable: '没有提取到可用的剧本文本。',
  document_structure_invalid: '剧本文本结构无法安全解析。',
};

export function documentStatusVariant(
  status: ScreenplayDocumentStatus,
): 'neutral' | 'success' | 'warning' | 'destructive' {
  if (status === 'ready') return 'success';
  if (status === 'failed') return 'destructive';
  if (status === 'uploading' || status === 'verifying') return 'warning';
  return 'neutral';
}

export function documentErrorLabel(
  document: ScreenplayDocument,
): string | null {
  return document.error_code ? errorLabels[document.error_code] : null;
}

export function languageLabel(value: string | null): string {
  if (value === 'zh-CN') return '中文';
  if (value === 'en-US') return '英文';
  if (value === 'mixed') return '中英混合';
  if (value === 'unknown') return '未识别';
  return '等待解析';
}

export function qualityWarningLabel(value: string): string {
  if (value === 'scene_heading_missing') {
    return '未识别到明确场景标题，正文已作为单一场景处理。';
  }
  return '文档存在需要人工核对的结构问题。';
}

export function formatDocumentDate(value: string): string {
  return dateFormatter.format(new Date(value));
}

export function formatDocumentSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

const dateFormatter = new Intl.DateTimeFormat('zh-CN', {
  dateStyle: 'medium',
  timeStyle: 'short',
});
