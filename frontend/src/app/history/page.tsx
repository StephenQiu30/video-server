import { ProtectedRoute } from '@/components/auth/protected-route';
import DownloadHistoryView from '@/components/downloads/download-history-view';

export const metadata = { title: '下载记录' };

export default function HistoryPage() {
  return (
    <ProtectedRoute>
      <DownloadHistoryView />
    </ProtectedRoute>
  );
}
