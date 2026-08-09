import { getDownloadAnalytics as getDownloadAnalyticsRequest } from '@/services/video/admin';

export type AnalyticsPeriod = 7 | 30 | 90;
export type AdminDownloadAnalytics = Awaited<
  ReturnType<typeof getDownloadAnalyticsRequest>
>;

export function getAdminDownloadAnalytics(
  days: AnalyticsPeriod,
): Promise<AdminDownloadAnalytics> {
  return getDownloadAnalyticsRequest({ days });
}

export { displayError } from '@/requestErrorConfig';
