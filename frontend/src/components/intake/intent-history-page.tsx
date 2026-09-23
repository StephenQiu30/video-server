'use client';

import { useRouter } from 'next/navigation';
import { useIntakeDraft } from '@/components/intake/intake-draft-provider';
import { IntentHistory } from '@/components/intake/intent-history';
import { useDownloadIntent } from '@/components/intake/use-download-intent';
import { markNavigationPush } from '@/components/layout/navigation-history';

export function IntentHistoryPage() {
  const router = useRouter();
  const intent = useDownloadIntent();
  const { setInput, setMode, setSelectedFormatId } = useIntakeDraft();

  return (
    <IntentHistory
      disabled={intent.cancelling || !!intent.attempt?.submitting}
      onResume={(id) => {
        if (!intent.resume(id)) return;
        setMode('link');
        setInput('');
        setSelectedFormatId('');
        markNavigationPush('/');
        router.push('/');
      }}
    />
  );
}
