import { ProtectedRoute } from '@/components/auth/protected-route';
import { ProviderStatusView } from '@/components/providers/provider-status-view';

export const metadata = { title: '平台状态' };

export default function ProvidersPage() {
  return (
    <ProtectedRoute>
      <div className="inner-page">
        <ProviderStatusView />
      </div>
    </ProtectedRoute>
  );
}
