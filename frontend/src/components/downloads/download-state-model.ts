import { localizedErrorMessage } from '@/lib/error-messages';
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

const failureDetails: Record<string, string> = {
  'artifact is unavailable': '下载文件暂时不可用，请重新获取下载源。',
  'artifact path is unsafe': '下载文件路径校验失败，请重新获取下载源。',
  'artifact size is invalid': '下载文件大小校验失败，请重新获取下载源。',
  'artifact digest is invalid': '下载文件摘要校验失败，请重新获取下载源。',
  'artifact digest does not match': '下载文件内容校验失败，请重新获取下载源。',
  'artifact media metadata is invalid':
    '视频音视频流校验失败，请重新获取下载源。',
  'artifact container is unsupported':
    '视频封装格式暂不支持，请重新获取下载源。',
};

export function statusVariant(status: DownloadStatus) {
  if (status === 'succeeded') return 'success' as const;
  if (status === 'failed') return 'destructive' as const;
  if (status === 'retry_wait') return 'warning' as const;
  return 'neutral' as const;
}

export function statusHeading(job: DownloadJob) {
  const media = archiveLabel(job);
  if (job.status === 'queued') return '下载即将开始';
  if (job.status === 'running') return `正在准备${media}文件`;
  if (job.status === 'retry_wait') return '等待再次尝试';
  if (job.status === 'succeeded') {
    return job.file_available ? `${media}文件已就绪` : `${media}文件已清理`;
  }
  if (job.status === 'failed') return failureTitle(job.error_code);
  return '下载已取消';
}

export function statusDescription(job: DownloadJob) {
  const media = archiveLabel(job);
  if (job.status === 'queued')
    return '任务已经进入队列，开始后会实时更新进度。';
  if (job.status === 'running') return '正在完成媒体下载、封装与文件校验。';
  if (job.status === 'retry_wait')
    return '系统会在等待结束后自动继续当前任务。';
  if (job.status === 'succeeded' && job.file_available) {
    return job.media_kind === 'image_gallery' ||
      job.media_kind === 'video_collection'
      ? `${media}已经完成校验，可以直接保存 ZIP 文件。`
      : '视频已经完成校验，可以直接保存到你的设备。';
  }
  if (job.status === 'succeeded') return '下载记录仍然保留，可以重新创建任务。';
  if (job.status === 'failed') {
    if (job.error_code === 'provider_auth_required') {
      return '当前平台需要新的授权会话，系统无法继续获取文件。';
    }
    if (job.error_code === 'media_validation_failed') {
      return '下载源或生成文件已失效，系统会先刷新下载源再尝试。';
    }
    return '系统保留了失败记录，可以根据原因恢复下载。';
  }
  return '任务已经停止，随时可以重新创建下载。';
}

function archiveLabel(job: DownloadJob) {
  return job.media_kind === 'image_gallery'
    ? '图集'
    : job.media_kind === 'video_collection'
      ? '视频合集'
      : '视频';
}

export function executionTitle(job: DownloadJob) {
  if (job.status === 'succeeded' && job.file_available) {
    return '文件完整性验证通过';
  }
  if (job.status === 'succeeded') return '下载记录已保留';
  if (job.status === 'failed') return '等待恢复操作';
  if (job.status === 'cancelled') return '任务记录已保留';
  return '任务由隔离的媒体 Runner 执行';
}

export function displayStage(job: DownloadJob): string {
  if (job.status === 'succeeded') return '已完成';
  if (job.status === 'failed') return failureStage(job.error_code);
  if (job.status === 'cancelled') return '已取消';
  return job.stage ? stageLabels[job.stage] : '等待调度';
}

export function failureTitle(code: DownloadJob['error_code']): string {
  if (code === 'provider_auth_required') return '需要授权访问';
  if (code === 'provider_session_expired') return '授权会话已过期';
  if (code === 'media_validation_failed') return '下载源需要刷新';
  if (code === 'format_unavailable') return '当前格式不可用';
  return '下载未完成';
}

export function failureStage(code: DownloadJob['error_code']): string {
  if (
    code === 'provider_auth_required' ||
    code === 'provider_session_expired'
  ) {
    return '授权检查失败';
  }
  if (code === 'media_validation_failed' || code === 'format_unavailable') {
    return '下载源检查失败';
  }
  return localizedErrorMessage(code) ? '执行失败' : '需要恢复';
}

export function retryActionLabel(code: DownloadJob['error_code']): string {
  if (
    code === 'provider_auth_required' ||
    code === 'provider_session_expired'
  ) {
    return '使用授权会话重试';
  }
  if (code === 'media_validation_failed' || code === 'format_unavailable') {
    return '重新获取并下载';
  }
  return '重新下载';
}

export function failureDescription(job: DownloadJob): string {
  const detail = job.error_message?.trim();
  if (detail && detail !== job.error_code) {
    return (
      failureDetails[detail] ??
      localizedErrorMessage(job.error_code) ??
      '下载任务未能完成，请稍后重试。'
    );
  }
  return (
    localizedErrorMessage(job.error_code) ?? '下载任务未能完成，请稍后重试。'
  );
}
