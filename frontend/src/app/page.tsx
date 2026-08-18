import DownloadWorkspace from '@/components/intake/download-workspace';
import { ProtectedRoute } from '@/components/auth/protected-route';

export default function HomePage() {
  return (
    <ProtectedRoute>
      <DownloadWorkspace />
    </ProtectedRoute>
  );
}
