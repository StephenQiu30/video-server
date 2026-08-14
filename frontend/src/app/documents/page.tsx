import { ProtectedRoute } from '@/components/protected-route';
import ScreenplayDocumentsView from '@/components/screenplay-documents-view';

export const metadata = { title: '剧本文档' };

export default function DocumentsPage() {
  return (
    <ProtectedRoute>
      <ScreenplayDocumentsView />
    </ProtectedRoute>
  );
}
