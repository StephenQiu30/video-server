import { AdminAiProvidersView } from '@/components/admin-ai-providers-view';
import { ProtectedRoute } from '@/components/protected-route';

export const metadata = { title: 'AI 服务' };

export default function AdminAiProvidersPage() {
  return (
    <ProtectedRoute requireAdmin>
      <main className="content-shell inner-page">
        <AdminAiProvidersView />
      </main>
    </ProtectedRoute>
  );
}
