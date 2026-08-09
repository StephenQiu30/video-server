import DownloadWorkspace from '@/components/download-workspace';
import { ProtectedRoute } from '@/components/protected-route';

export default function HomePage() {
  return (
    <ProtectedRoute>
      <DownloadWorkspace />
    </ProtectedRoute>
  );
}
