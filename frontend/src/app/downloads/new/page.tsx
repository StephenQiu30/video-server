import type { Metadata } from 'next';
import { Suspense } from 'react';

import { ProtectedRoute } from '@/components/auth/protected-route';
import InspectionRoute, {
  InspectionSkeleton,
} from '@/components/intake/inspection-route';

export const metadata: Metadata = { title: '解析结果' };

export default function NewDownloadPage() {
  return (
    <ProtectedRoute>
      <Suspense
        fallback={
          <div className="inner-page">
            <InspectionSkeleton />
          </div>
        }
      >
        <InspectionRoute />
      </Suspense>
    </ProtectedRoute>
  );
}
