export enum AnalysisStatusCode {
  Queued = 'queued',
  Running = 'running',
  RetryWait = 'retry_wait',
  Succeeded = 'succeeded',
  Failed = 'failed',
  Cancelled = 'cancelled',
}

export enum AnalysisReportStatusCode {
  Publishing = 'publishing',
  PublishFailed = 'publish_failed',
  Available = 'available',
}

export enum AnalysisStageCode {
  Preparing = 'preparing',
  Analyzing = 'analyzing',
  Validating = 'validating',
  Publishing = 'publishing',
}

type AnalysisStatusPresentation = {
  label: string;
  active: boolean;
};

const analysisStatusPresentation = {
  [AnalysisStatusCode.Queued]: {
    label: '等待分析',
    active: true,
  },
  [AnalysisStatusCode.Running]: {
    label: '正在分析',
    active: true,
  },
  [AnalysisStatusCode.RetryWait]: {
    label: '等待重试',
    active: true,
  },
  [AnalysisStatusCode.Succeeded]: {
    label: '分析已完成',
    active: false,
  },
  [AnalysisStatusCode.Failed]: {
    label: '分析失败',
    active: false,
  },
  [AnalysisStatusCode.Cancelled]: {
    label: '分析已取消',
    active: false,
  },
} satisfies Record<API.AnalysisStatus, AnalysisStatusPresentation>;

export const statusLabels = {
  [AnalysisStatusCode.Queued]:
    analysisStatusPresentation[AnalysisStatusCode.Queued].label,
  [AnalysisStatusCode.Running]:
    analysisStatusPresentation[AnalysisStatusCode.Running].label,
  [AnalysisStatusCode.RetryWait]:
    analysisStatusPresentation[AnalysisStatusCode.RetryWait].label,
  [AnalysisStatusCode.Succeeded]:
    analysisStatusPresentation[AnalysisStatusCode.Succeeded].label,
  [AnalysisStatusCode.Failed]:
    analysisStatusPresentation[AnalysisStatusCode.Failed].label,
  [AnalysisStatusCode.Cancelled]:
    analysisStatusPresentation[AnalysisStatusCode.Cancelled].label,
} satisfies Record<API.AnalysisStatus, string>;

export function isActiveAnalysisStatus(status: API.AnalysisStatus): boolean {
  return analysisStatusPresentation[status].active;
}

export function isTerminalAnalysisStatus(status: API.AnalysisStatus): boolean {
  return !isActiveAnalysisStatus(status);
}

const analysisReportStatusLabels: Record<AnalysisReportStatusCode, string> = {
  [AnalysisReportStatusCode.Publishing]: '新报告文件生成中',
  [AnalysisReportStatusCode.PublishFailed]: '报告文件生成失败，等待恢复',
  [AnalysisReportStatusCode.Available]: '上一版本报告',
};

export function analysisReportStatusLabel(status?: string): string {
  return status && Object.hasOwn(analysisReportStatusLabels, status)
    ? analysisReportStatusLabels[status as AnalysisReportStatusCode]
    : analysisReportStatusLabels[AnalysisReportStatusCode.Available];
}

export const stageLabels: Record<API.AnalysisStage, string> = {
  [AnalysisStageCode.Preparing]: '准备输入',
  [AnalysisStageCode.Analyzing]: '执行 AI 分析',
  [AnalysisStageCode.Validating]: '校验结构化结果',
  [AnalysisStageCode.Publishing]: '生成报告文件',
};

export function screenplayAnalysisErrorMessage(
  code: string | null | undefined,
): string | undefined {
  if (code === 'analysis_resource_limit') {
    return '剧本任务达到当前执行器资源上限，未发布部分结果；请稍后重试，持续出现时联系管理员调整分析配置。';
  }
  if (code === 'screenplay_output_incomplete') {
    return '剧本改写结果不完整，任务未发布任何部分正文，请重试。';
  }
  if (
    code === 'analysis_artifact_unavailable' ||
    code === 'input_artifact_unavailable'
  ) {
    return '规范化剧本文档已失效，请重新导入后再分析。';
  }
  if (code === 'invalid_model_output') {
    return 'AI 返回的剧本结果未通过结构、证据或覆盖校验，未发布部分结果。';
  }
  return undefined;
}
