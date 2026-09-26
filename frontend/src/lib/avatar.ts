export function avatarUrl(
  user: Pick<API.UserResponse, 'avatar_version'>,
): string | undefined {
  return user.avatar_version
    ? `/api/users/me/avatar?version=${user.avatar_version}`
    : undefined;
}
