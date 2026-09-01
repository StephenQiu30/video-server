import type { DownloadJob, DownloadStage, DownloadStatus } from '@/types/video';

export const statusLabels: Record<DownloadStatus, string> = {
  queued: '等待处理',
  running: '正在下载',
  retry_wait: '等待重试',
  succeeded: '下载已完成',
  failed: '下载失败',
  cancelled: '任务已取消',
};

const stageLabels: Record<DownloadStage, string> = {
  revalidating: '重新验证',
  downloading: '下载媒体',
  remuxing: '封装媒体',
  verifying: '校验文件',
  uploading: '保存制品',
};

export function statusVariant(status: DownloadStatus) {
  if (status === 'succeeded') return 'success' as const;
  if (status === 'failed') return 'destructive' as const;
  if (status === 'retry_wait') return 'warning' as const;
  return 'neutral' as const;
}

export function statusHeading(job: DownloadJob) {
  const media = job.media_kind === 'image_gallery' ? '图集' : '视频';
  if (job.status === 'queued') return '下载即将开始';
  if (job.status === 'running') return `正在准备${media}文件`;
  if (job.status === 'retry_wait') return '等待再次尝试';
  if (job.status === 'succeeded') {
    return job.file_available ? `${media}文件已就绪` : `${media}文件已清理`;
  }
  if (job.status === 'failed') return '下载没有完成';
  return '下载已取消';
}

export function statusDescription(job: DownloadJob) {
  if (job.status === 'queued')
    return '任务已经进入队列，开始后会实时更新进度。';
  if (job.status === 'running') return '正在完成媒体下载、封装与文件校验。';
  if (job.status === 'retry_wait')
    return '系统会在等待结束后自动继续当前任务。';
  if (job.status === 'succeeded' && job.file_available) {
    return job.media_kind === 'image_gallery'
      ? '图集已经完成校验，可以直接保存 ZIP 文件。'
      : '视频已经完成校验，可以直接保存到你的设备。';
  }
  if (job.status === 'succeeded') return '下载记录仍然保留，可以重新创建任务。';
  if (job.status === 'failed') return '查看失败原因后，可以重新创建下载任务。';
  return '任务已经停止，随时可以重新创建下载。';
}

export function executionTitle(job: DownloadJob) {
  if (job.status === 'succeeded' && job.file_available) {
    return '文件完整性验证通过';
  }
  if (job.status === 'succeeded') return '下载记录已保留';
  if (job.status === 'failed') return '失败记录已保留';
  if (job.status === 'cancelled') return '任务记录已保留';
  return '任务由隔离的媒体 Runner 执行';
}

export function displayStage(job: DownloadJob): string {
  if (job.status === 'succeeded') return '已完成';
  if (job.status === 'failed') return '已失败';
  if (job.status === 'cancelled') return '已取消';
  return job.stage ? stageLabels[job.stage] : '等待调度';
}
