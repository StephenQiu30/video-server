import type {
  ScreenplayDocument,
  ScreenplayDocumentPage,
  ScreenplayDocumentSummary,
} from '@/types/video';

export const documentId = '99999999-9999-4999-8999-999999999999';

export function screenplayDocumentSummary(
  overrides: Partial<ScreenplayDocumentSummary> = {},
): ScreenplayDocumentSummary {
  return {
    id: documentId,
    title: '午夜来客',
    original_filename: 'midnight-visitor.fountain',
    source_format: 'fountain',
    declared_size_bytes: 4096,
    status: 'ready',
    attempt: 1,
    error_code: null,
    version: 2,
    detected_language: 'mixed',
    scene_count: 2,
    character_count: 1280,
    quality_warnings: [],
    created_at: '2026-08-14T10:00:00Z',
    updated_at: '2026-08-14T10:02:00Z',
    finished_at: '2026-08-14T10:02:00Z',
    ...overrides,
  };
}

export function screenplayDocument(
  overrides: Partial<ScreenplayDocument> = {},
): ScreenplayDocument {
  return {
    ...screenplayDocumentSummary(),
    preview: '<script>只作为台词文本</script>\n\nINT. LOBBY - NIGHT\n',
    preview_truncated: true,
    quality_warnings: ['scene_heading_missing'],
    ...overrides,
  };
}

export function screenplayDocumentPage(
  overrides: Partial<ScreenplayDocumentPage> = {},
): ScreenplayDocumentPage {
  return {
    items: [screenplayDocumentSummary()],
    page: 1,
    page_size: 20,
    total: 1,
    ...overrides,
  };
}
