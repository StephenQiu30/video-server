const integerFormatter = new Intl.NumberFormat('zh-CN');
const percentFormatter = new Intl.NumberFormat('zh-CN', {
  maximumFractionDigits: 1,
  minimumFractionDigits: 0,
});
const dateFormatter = new Intl.DateTimeFormat('zh-CN', {
  month: 'short',
  day: 'numeric',
  timeZone: 'UTC',
});

export function formatInteger(value: number): string {
  return integerFormatter.format(value);
}

export function formatPercent(value: number): string {
  return `${percentFormatter.format(value)}%`;
}

export function formatBytes(value: number): string {
  if (value < 1024) return `${formatInteger(value)} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let current = value / 1024;
  let index = 0;
  while (current >= 1024 && index < units.length - 1) {
    current /= 1024;
    index += 1;
  }
  return `${new Intl.NumberFormat('zh-CN', {
    maximumFractionDigits: current >= 100 ? 0 : 1,
  }).format(current)} ${units[index]}`;
}

export function formatDuration(value: number): string {
  const seconds = Math.max(0, Math.round(value));
  if (seconds < 60) return `${seconds} 秒`;
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  if (minutes < 60) return `${minutes} 分 ${remainder} 秒`;
  const hours = Math.floor(minutes / 60);
  return `${hours} 小时 ${minutes % 60} 分`;
}

export function formatShortDate(value: string): string {
  const normalized = value.includes('T') ? value : `${value}T00:00:00Z`;
  return dateFormatter.format(new Date(normalized));
}

export function formatDateRange(start: string, end: string): string {
  return `${formatShortDate(start)}至${formatShortDate(end)}`;
}
