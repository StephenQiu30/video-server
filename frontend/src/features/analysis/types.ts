export type AnalysisProfile = 'standard-v1';
export type OutputLanguage = 'zh-CN' | 'en-US';

export type AnalysisStatus =
  | 'queued'
  | 'running'
  | 'retry_wait'
  | 'succeeded'
  | 'failed'
  | 'cancelled';

export type AnalysisStage =
  | 'preparing'
  | 'transcribing'
  | 'analyzing'
  | 'validating';

export type EvidenceStatement = {
  text: string;
  evidence_segment_ids: string[];
};

export type AnalysisChapter = {
  title: string;
  start_ms: number;
  end_ms: number;
  summary: string;
  evidence_segment_ids: string[];
};

export type MindMapNode = {
  id: string;
  title: string;
  summary: string | null;
  start_ms: number | null;
  evidence_segment_ids: string[];
  children: MindMapNode[];
};

export type AnalysisResult = {
  language: string;
  title: string;
  summary: EvidenceStatement;
  key_points: EvidenceStatement[];
  action_items: EvidenceStatement[];
  chapters: AnalysisChapter[];
  mind_map: MindMapNode;
};

export type AnalysisJob = {
  id: string;
  profile: string;
  output_language: string;
  status: AnalysisStatus;
  stage: AnalysisStage | null;
  progress: number;
  attempt: number;
  error_code: string | null;
  created_at: string;
  updated_at: string;
  finished_at: string | null;
  result: AnalysisResult | null;
};

export type CreateAnalysisInput = {
  profile: AnalysisProfile;
  output_language: OutputLanguage;
};

export const terminalAnalysisStatuses = new Set<AnalysisStatus>([
  'succeeded',
  'failed',
  'cancelled',
]);
