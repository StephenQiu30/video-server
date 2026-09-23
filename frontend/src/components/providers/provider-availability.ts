const READY_ACCESS_STATES = new Set<API.ProviderAccessState>([
  'public_ready',
  'guest_ready',
  'operator_ready',
]);

const UNAVAILABLE_STATUSES = new Set<API.ProviderSupportStatus>([
  'access_required',
  'degraded',
  'rate_limited',
  'blocked',
  'disabled',
  'unsupported',
]);

export function isCurrentlyAvailable(
  provider: API.ProviderListResponse['items'][number],
): boolean {
  return (
    provider.download_available &&
    READY_ACCESS_STATES.has(provider.access_state) &&
    !UNAVAILABLE_STATUSES.has(provider.status)
  );
}
