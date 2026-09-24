import { Suspense } from 'react';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { IntentHistoryPage } from '@/components/intake/intent-history-page';

export const metadata = { title: '我的处理记录' };

export default function InspectionsHistoryPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<p role="status">正在读取我的处理记录…</p>}>
        <IntentHistoryPage />
      </Suspense>
    </ProtectedRoute>
  );
}
