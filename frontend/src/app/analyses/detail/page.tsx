import { Suspense } from 'react';
import AnalysisDetailRoute from '@/components/analysis/analysis-detail-route';
import { ProtectedRoute } from '@/components/auth/protected-route';

export const metadata = { title: '分析详情' };

export default function AnalysisDetailPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<p role="status">正在读取分析…</p>}>
        <AnalysisDetailRoute />
      </Suspense>
    </ProtectedRoute>
  );
}
