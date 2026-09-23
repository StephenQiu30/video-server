import { describe, expect, it } from 'vitest';
import {
  AnalysisReportStatusCode,
  analysisReportStatusLabel,
  screenplayAnalysisErrorMessage,
} from '@/components/analysis/analysis-panel-model';

describe('analysis report status presentation', () => {
  it.each([
    [AnalysisReportStatusCode.Validated, '报告等待生成'],
    [AnalysisReportStatusCode.Publishing, '新报告文件生成中'],
    [AnalysisReportStatusCode.Available, '上一版本报告'],
    [AnalysisReportStatusCode.PublishFailed, '报告文件生成失败，等待恢复'],
    [AnalysisReportStatusCode.DeletePending, '报告文件正在清理'],
    [AnalysisReportStatusCode.Deleted, '报告文件已清理'],
  ] as const)('labels %s using its lifecycle state', (status, label) => {
    expect(analysisReportStatusLabel(status)).toBe(label);
  });

  it('does not present a missing report as an available previous version', () => {
    expect(analysisReportStatusLabel()).toBe('报告尚未生成');
  });

  it('does not mislabel a status from a newer backend as an available report', () => {
    expect(
      analysisReportStatusLabel('archiving' as API.AnalysisReportStatus),
    ).toBe('报告状态更新中');
  });
});

describe('screenplay analysis error presentation', () => {
  it('uses the backend analysis error contract for document loss', () => {
    expect(screenplayAnalysisErrorMessage('input_artifact_unavailable')).toBe(
      '规范化剧本文档已失效，请重新导入后再分析。',
    );
  });

  it('leaves unrelated errors to the shared error presenter', () => {
    expect(
      screenplayAnalysisErrorMessage('analysis_cli_failed'),
    ).toBeUndefined();
  });
});
