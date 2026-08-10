import { ProtectedRoute } from '@/components/protected-route';
import { ProviderStatusView } from '@/components/provider-status-view';

export const metadata = { title: '平台状态' };

export default function ProvidersPage() {
  return (
    <ProtectedRoute>
      <main className="content-shell py-14 sm:py-20 lg:py-24">
        <ProviderStatusView />
      </main>
    </ProtectedRoute>
  );
}
