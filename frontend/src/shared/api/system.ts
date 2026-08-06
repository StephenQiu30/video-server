import { readyHealthReadyGet } from '@/api/system';

export type SystemReady = {
  status: 'ok';
  service: 'api';
};

export async function getSystemReady(): Promise<SystemReady> {
  try {
    return (await readyHealthReadyGet()) as SystemReady;
  } catch {
    throw new Error('server_not_ready');
  }
}
