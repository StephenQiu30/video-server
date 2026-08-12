import {
  createProviderCatalogEntry as createProviderCatalogEntryRequest,
  deleteProviderCatalogEntry as deleteProviderCatalogEntryRequest,
  listProviderCatalogEntries as listProviderCatalogEntriesRequest,
  updateProviderCatalogEntry as updateProviderCatalogEntryRequest,
} from '@/services/video/admin';

export function listProviderCatalogEntries(): Promise<API.ProviderCatalogListResponse> {
  return listProviderCatalogEntriesRequest();
}

export function createProviderCatalogEntry(
  input: API.CreateProviderCatalogEntryRequest,
): Promise<API.ProviderCatalogEntryResponse> {
  return createProviderCatalogEntryRequest(input);
}

export function updateProviderCatalogEntry(
  key: string,
  input: API.UpdateProviderCatalogEntryRequest,
): Promise<API.ProviderCatalogEntryResponse> {
  return updateProviderCatalogEntryRequest(
    { provider_key: encodeURIComponent(key) },
    input,
  );
}

export function deleteProviderCatalogEntry(key: string): Promise<unknown> {
  return deleteProviderCatalogEntryRequest({
    provider_key: encodeURIComponent(key),
  });
}

export { displayError } from '@/lib/request-error';
