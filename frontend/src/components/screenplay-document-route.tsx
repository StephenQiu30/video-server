'use client';

import { useSearchParams } from 'next/navigation';
import { MissingScreenplayDocument } from '@/components/missing-screenplay-document';
import ScreenplayDocumentDetailView from '@/components/screenplay-document-detail-view';

export default function ScreenplayDocumentRoute() {
  const searchParams = useSearchParams();
  const documentId = searchParams?.get('documentId')?.trim() ?? '';
  return documentId ? (
    <ScreenplayDocumentDetailView documentId={documentId} />
  ) : (
    <MissingScreenplayDocument />
  );
}
