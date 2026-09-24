import { Suspense } from 'react';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { IntentHistoryPage } from '@/components/intake/intent-history-page';

export const metadata = { title: '解析中心' };

export default function InspectionsHistoryPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<p role="status">正在读取解析中心…</p>}>
        <IntentHistoryPage />
      </Suspense>
    </ProtectedRoute>
  );
}
