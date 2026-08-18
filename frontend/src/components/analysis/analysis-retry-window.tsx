import type { AnalysisJob } from '@/types/video';

export default function AnalysisRetryWindow({ job }: { job: AnalysisJob }) {
  if (!job.retry_available_until) {
    return (
      <p className="text-sm text-muted-foreground">
        原视频重试窗口不可用；已有报告不受影响。
      </p>
    );
  }
  const label = new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(job.retry_available_until));
  return (
    <p className="text-sm text-muted-foreground">
      原视频可重试至 <time dateTime={job.retry_available_until}>{label}</time>
    </p>
  );
}
