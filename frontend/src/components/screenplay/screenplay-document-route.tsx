'use client';

import { useSearchParams } from 'next/navigation';
import { MissingScreenplayDocument } from '@/components/screenplay/missing-screenplay-document';
import ScreenplayDocumentDetailView from '@/components/screenplay/screenplay-document-detail-view';

export default function ScreenplayDocumentRoute() {
  const searchParams = useSearchParams();
  const documentId = searchParams?.get('documentId')?.trim() ?? '';
  const analysisId = searchParams?.get('analysisId')?.trim() || undefined;
  return documentId ? (
    <ScreenplayDocumentDetailView
      documentId={documentId}
      analysisId={analysisId}
    />
  ) : (
    <MissingScreenplayDocument />
  );
}
