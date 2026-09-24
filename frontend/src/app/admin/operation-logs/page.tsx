import { OperationLogsView } from '@/components/admin/operation-logs-view';
import { ProtectedRoute } from '@/components/auth/protected-route';
export const metadata = { title: '系统操作日志' };
export default function OperationLogsPage() {
  return (
    <ProtectedRoute requireAdmin>
      <OperationLogsView />
    </ProtectedRoute>
  );
}
