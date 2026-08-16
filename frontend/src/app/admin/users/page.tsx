import { AdminUsersView } from '@/components/admin-users-view';
import { ProtectedRoute } from '@/components/protected-route';

export const metadata = { title: '用户管理' };

export default function AdminUsersPage() {
  return (
    <ProtectedRoute requireAdmin>
      <div className="inner-page">
        <AdminUsersView />
      </div>
    </ProtectedRoute>
  );
}
