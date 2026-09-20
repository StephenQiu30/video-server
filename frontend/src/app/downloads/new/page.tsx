import type { Metadata } from 'next';

import { ProtectedRoute } from '@/components/auth/protected-route';
import DownloadWorkspace from '@/components/intake/download-workspace';
import { BackLink } from '@/components/layout/back-link';

export const metadata: Metadata = { title: '新建下载' };

export default function NewDownloadPage() {
  return (
    <ProtectedRoute>
      <div className="inner-page">
        <BackLink fallbackHref="/" />
        <DownloadWorkspace />
      </div>
    </ProtectedRoute>
  );
}
