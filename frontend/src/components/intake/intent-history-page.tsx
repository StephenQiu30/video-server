'use client';

import { useRouter } from 'next/navigation';
import { useIntakeDraft } from '@/components/intake/intake-draft-provider';
import { IntentHistory } from '@/components/intake/intent-history';
import { useDownloadIntent } from '@/components/intake/use-download-intent';
import { markNavigationPush } from '@/components/layout/navigation-history';

export function IntentHistoryPage() {
  const router = useRouter();
  const intent = useDownloadIntent();
  const { setInput, setMode } = useIntakeDraft();

  return (
    <IntentHistory
      disabled={intent.cancelling || !!intent.attempt?.submitting}
      onResume={(item) => {
        if (item.status === 'ready' && item.inspection_id) {
          const target = `/downloads/new?inspectionId=${encodeURIComponent(item.inspection_id)}&intentId=${encodeURIComponent(item.id)}`;
          markNavigationPush(target);
          router.push(target);
          return;
        }
        if (item.status === 'handed_off' && item.job_id) {
          const target = `/downloads/detail?jobId=${encodeURIComponent(item.job_id)}`;
          markNavigationPush(target);
          router.push(target);
          return;
        }
        if (!intent.resume(item.id)) return;
        setMode('link');
        setInput('');
        markNavigationPush('/');
        router.push('/');
      }}
    />
  );
}
