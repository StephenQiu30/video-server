import DownloadHistoryView from '@/components/download-history-view';
import { ProtectedRoute } from '@/components/protected-route';

export const metadata = { title: '下载历史' };

export default function HistoryPage() {
  return (
    <ProtectedRoute>
      <DownloadHistoryView />
    </ProtectedRoute>
  );
}
