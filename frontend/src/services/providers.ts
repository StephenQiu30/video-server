import { listProviders as listProvidersRequest } from '@/services/video/providers';

export type ProviderStatusList = Awaited<
  ReturnType<typeof listProvidersRequest>
>;
export type ProviderStatus = ProviderStatusList['items'][number];

export function listProviders(): Promise<ProviderStatusList> {
  return listProvidersRequest();
}

export { displayError } from '@/lib/request-error';
