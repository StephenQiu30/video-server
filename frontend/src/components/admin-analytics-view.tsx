'use client';

import { useState } from 'react';

import { AdminAnalyticsScreen } from '@/components/admin-analytics/admin-analytics-screen';
import { useAdminDownloadAnalytics } from '@/hooks/useAdminDownloadAnalytics';
import type { AnalyticsPeriod } from '@/services/analytics';

export function AdminAnalyticsView() {
  const [days, setDays] = useState<AnalyticsPeriod>(30);
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
