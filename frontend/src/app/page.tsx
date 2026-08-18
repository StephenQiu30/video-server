import { ProtectedRoute } from '@/components/auth/protected-route';
import DownloadWorkspace from '@/components/intake/download-workspace';

export default function HomePage() {
  return (
    <ProtectedRoute>
      <DownloadWorkspace />
    </ProtectedRoute>
  );
}
