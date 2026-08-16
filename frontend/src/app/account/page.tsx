import { AccountView } from '@/components/account-view';
import { ProtectedRoute } from '@/components/protected-route';

export const metadata = { title: '账户' };

export default function AccountPage() {
  return (
    <ProtectedRoute>
      <div className="inner-page">
        <AccountView />
      </div>
    </ProtectedRoute>
  );
}
