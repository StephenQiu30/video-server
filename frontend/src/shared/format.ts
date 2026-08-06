export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remaining = String(Math.floor(seconds % 60)).padStart(2, '0');
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, '0')}:${remaining}`
    : `${minutes}:${remaining}`;
}

export function formatMilliseconds(milliseconds: number): string {
  return formatDuration(Math.floor(milliseconds / 1000));
}
