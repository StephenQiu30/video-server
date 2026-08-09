export function authRedirect(search: string): string {
  const redirect = new URLSearchParams(search).get('redirect');
  if (
    !redirect?.startsWith('/') ||
    redirect.startsWith('//') ||
    redirect.includes('\\') ||
    redirect.startsWith('/user/')
  ) {
    return '/';
  }
  return redirect;
}
