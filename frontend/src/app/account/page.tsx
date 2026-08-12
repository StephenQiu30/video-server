import { AccountView } from '@/components/account-view';
import { ProtectedRoute } from '@/components/protected-route';

export const metadata = { title: '账户' };

export default function AccountPage() {
  return (
    <ProtectedRoute>
      <main className="content-shell inner-page">
        <AccountView />
      </main>
    </ProtectedRoute>
  );
}
