import { AdminProviderCatalogView } from '@/components/admin-provider-catalog-view';
import { ProtectedRoute } from '@/components/protected-route';

export const metadata = { title: '平台目录' };

export default function AdminProvidersPage() {
  return (
    <ProtectedRoute requireAdmin>
      <main className="content-shell inner-page">
        <AdminProviderCatalogView />
      </main>
    </ProtectedRoute>
  );
}
