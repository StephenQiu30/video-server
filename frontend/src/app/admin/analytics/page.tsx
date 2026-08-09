import { AdminAnalyticsView } from '@/components/admin-analytics-view';
import { ProtectedRoute } from '@/components/protected-route';

export const metadata = { title: '下载分析' };

export default function AdminAnalyticsPage() {
  return (
    <ProtectedRoute requireAdmin>
      <main className="content-shell py-14 sm:py-20 lg:py-24">
        <AdminAnalyticsView />
      </main>
    </ProtectedRoute>
  );
}
