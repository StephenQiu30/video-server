import { AdminAnalyticsView } from '@/components/admin-analytics-view';
import { ProtectedRoute } from '@/components/protected-route';

export const metadata = { title: '下载分析' };

export default function AdminAnalyticsPage() {
  return (
    <ProtectedRoute requireAdmin>
      <div className="inner-page">
        <AdminAnalyticsView />
      </div>
    </ProtectedRoute>
  );
}
