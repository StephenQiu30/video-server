'use client';

import { useState } from 'react';

import { AdminAnalyticsScreen } from '@/components/admin/admin-analytics/admin-analytics-screen';
import { useAdminDownloadAnalytics } from '@/components/admin/admin-analytics/use-download-analytics';

export function AdminAnalyticsView() {
  const [days, setDays] = useState<7 | 30 | 90>(30);
  const state = useAdminDownloadAnalytics(days);

  return (
    <AdminAnalyticsScreen
      data={state.data}
      days={days}
      error={state.error}
      loading={state.loading}
      onDaysChange={setDays}
      onRetry={state.retry}
    />
  );
}
