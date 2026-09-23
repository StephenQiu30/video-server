import { ProtectedRoute } from '@/components/auth/protected-route';
import { IntentHistoryPage } from '@/components/intake/intent-history-page';

export const metadata = { title: '解析记录' };

export default function InspectionsHistoryPage() {
  return (
    <ProtectedRoute>
      <IntentHistoryPage />
    </ProtectedRoute>
  );
}
