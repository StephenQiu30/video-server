export function authRedirect(search: string): string {
  const redirect = new URLSearchParams(search).get('redirect');
  if (
    !redirect?.startsWith('/') ||
    redirect.startsWith('//') ||
    redirect.startsWith('/user/')
  ) {
    return '/';
  }
  return redirect;
}
