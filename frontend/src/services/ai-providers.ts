import {
  activateAiProviderProfile as activateRequest,
  createAiProviderProfile as createRequest,
  deleteAiProviderProfile as deleteRequest,
  listAiProviderProfiles as listRequest,
  updateAiProviderProfile as updateRequest,
} from '@/services/video/admin';

export function listAiProviderProfiles(): Promise<API.AiProviderProfileListResponse> {
  return listRequest();
}

export function createAiProviderProfile(
  input: API.CreateAiProviderProfileRequest,
): Promise<API.AiProviderProfileResponse> {
  return createRequest(input);
}

export function updateAiProviderProfile(
  key: string,
  input: API.UpdateAiProviderProfileRequest,
): Promise<API.AiProviderProfileResponse> {
  return updateRequest({ provider_key: encodeURIComponent(key) }, input);
}

export function activateAiProviderProfile(
  key: string,
): Promise<API.AiProviderProfileResponse> {
  return activateRequest({ provider_key: encodeURIComponent(key) });
}

export function deleteAiProviderProfile(key: string): Promise<unknown> {
  return deleteRequest({ provider_key: encodeURIComponent(key) });
}

export { displayError } from '@/lib/request-error';
