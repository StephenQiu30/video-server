import {
  getLiveness as getLivenessRequest,
  getReadiness as getReadinessRequest,
} from '@/services/video/system';

export function getLiveness(): Promise<API.LivenessResponse> {
  return getLivenessRequest();
}

export function getReadiness(): Promise<API.ReadinessResponse> {
  return getReadinessRequest();
}
