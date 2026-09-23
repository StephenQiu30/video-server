export function intentTitle(status?: API.IntentStatus) {
  switch (status) {
    case 'queued':
      return '等待解析';
    case 'preparing':
      return '正在准备解析';
    case 'resolving':
      return '正在读取媒体信息';
    case 'retry_wait':
      return '正在自动恢复';
    case 'action_required':
      return '此内容需要额外权限';
    case 'ready':
      return '解析完成';
    case 'handed_off':
      return '下载任务已创建';
    case 'cancelled':
      return '解析已取消';
    case 'expired':
      return '本次解析已超时';
    case 'failed':
      return '本次解析未完成';
    default:
      return '正在确认解析任务';
  }
}

export function intentStatusVariant(
  status: API.IntentStatus,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'ready' || status === 'handed_off') return 'default';
  if (status === 'failed') return 'destructive';
  if (
    status === 'cancelled' ||
    status === 'expired' ||
    status === 'action_required'
  )
    return 'outline';
  return 'secondary';
}
