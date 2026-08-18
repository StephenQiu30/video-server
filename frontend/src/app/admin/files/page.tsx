import { AdminStorageView } from '@/components/admin/admin-storage-view';
import { ProtectedRoute } from '@/components/auth/protected-route';

export const metadata = { title: '文件管理' };

export default function AdminFilesPage() {
  return (
    <ProtectedRoute requireAdmin>
      <div className="inner-page">
        <AdminStorageView />
      </div>
    </ProtectedRoute>
  );
}
