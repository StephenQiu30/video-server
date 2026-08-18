import { ProtectedRoute } from '@/components/auth/protected-route';
import ScreenplayDocumentsView from '@/components/screenplay/screenplay-documents-view';

export const metadata = { title: '剧本文档' };

export default function DocumentsPage() {
  return (
    <ProtectedRoute>
      <ScreenplayDocumentsView />
    </ProtectedRoute>
  );
}
