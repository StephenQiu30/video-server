export const STORAGE_PAGE_SIZE = 20;

export const storageCategoryLabels: Record<API.StoredFileCategory, string> = {
  video: '视频文件',
  screenplay: '剧本文档',
  analysis_report: '分析报告',
};

export function formatStorageSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / 1024;
  let unit = units[0];
  for (const next of units.slice(1)) {
    if (value < 1024) break;
    value /= 1024;
    unit = next;
  }
  return `${value.toLocaleString('zh-CN', { maximumFractionDigits: 1 })} ${unit}`;
}

export function formatStorageDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}
