import {
  listUsers as listUsersRequest,
  updateUserAccess as updateUserAccessRequest,
} from '@/services/video/admin';
import { updateCurrentUser as updateCurrentUserRequest } from '@/services/video/users';

export function updateCurrentUser(
  input: API.UpdateProfileRequest,
): Promise<API.UserResponse> {
  return updateCurrentUserRequest(input);
}

export function listUsers(
  params: API.listUsersParams,
): Promise<API.ManagedUserListResponse> {
  return listUsersRequest(params);
}

export function updateUserAccess(
  userId: string,
  input: API.UpdateUserAccessRequest,
): Promise<API.ManagedUserResponse> {
  return updateUserAccessRequest(
    { user_id: encodeURIComponent(userId) },
    input,
  );
}

export { displayError } from '@/requestErrorConfig';
