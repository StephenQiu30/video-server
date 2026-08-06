export type SystemReady = {
  status: 'ok';
  service: 'api';
};

export async function getSystemReady(): Promise<SystemReady> {
  const response = await fetch('/health/ready', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error('server_not_ready');
  }
  return response.json() as Promise<SystemReady>;
}
