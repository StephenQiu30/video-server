import { AdminAiProvidersView } from '@/components/admin/admin-ai-providers-view';
import { ProtectedRoute } from '@/components/auth/protected-route';

export const metadata = { title: 'AI 服务' };

export default function AdminAiProvidersPage() {
  return (
    <ProtectedRoute requireAdmin>
      <div className="inner-page">
        <AdminAiProvidersView />
      </div>
    </ProtectedRoute>
  );
}
