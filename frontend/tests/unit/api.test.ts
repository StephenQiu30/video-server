import { describe, expect, it } from 'vitest';

import {
  cancelAnalysis,
  createAnalysis,
  getAnalysis,
  listAnalysisSkills,
} from '@/services/analysis';
import { getAdminDownloadAnalytics } from '@/services/analytics';
import {
  getCurrentUser,
  login,
  logout,
  refreshSession,
  register,
} from '@/services/auth';
import {
  getScreenplayDocument,
  listScreenplayDocuments,
} from '@/services/documents';
import {
  cancelDownload,
  createDownload,
  createSourceDiscovery,
  getDownload,
  getDownloadHistory,
  getInspection,
  inspectDiscoveredItem,
  inspectMedia,
  issueDownloadUrl,
} from '@/services/download';
import {
  createProviderCatalogEntry,
  deleteProviderCatalogEntry,
  listProviderCatalogEntries,
  updateProviderCatalogEntry,
} from '@/services/provider-catalog';
import { getLiveness, getReadiness } from '@/services/system';
import {
  listUsers,
  updateCurrentUser,
  updateUserAccess,
} from '@/services/users';
import { analysisJob, analysisSkills } from '../fixtures/analysis-fixtures';
import {
  documentId,
  screenplayDocument,
  screenplayDocumentPage,
} from '../fixtures/document-fixtures';
import {
  inspection,
  job,
  sourceDiscovery,
} from '../fixtures/download-fixtures';
import { httpRequests, mockHttpResponses } from '../helpers/http';

describe('typed API client', () => {
  it('covers email registration, JWT session restore and logout endpoints', async () => {
    const user = {
      id: '11111111-1111-4111-8111-111111111111',
      username: 'video_user',
      email: 'user@example.com',
      role: 'user' as const,
      created_at: '2026-08-09T10:00:00Z',
      updated_at: '2026-08-09T10:00:00Z',
    };
    mockHttpResponses(user, user, user, user, undefined);

    await register({
      username: user.username,
      email: user.email,
      password: 'strong-pass-123',
    });
    await login({ email: user.email, password: 'strong-pass-123' });
    await getCurrentUser();
    await refreshSession();
    await logout();

    expect(httpRequests().map(({ url }) => url)).toEqual([
      '/api/auth/register',
      '/api/auth/login',
      '/api/auth/me',
      '/api/auth/refresh',
      '/api/auth/logout',
    ]);
  });

  it('uses same-origin download endpoints and idempotency headers', async () => {
    mockHttpResponses(inspection, job());
    await inspectMedia('https://media.example/owned', 'inspect-key');
    await createDownload(
      inspection.id,
      inspection.formats[0].id,
      'download-key',
    );

    expect(httpRequests()).toMatchObject([
      {
        url: '/api/inspections',
        method: 'POST',
        headers: expect.objectContaining({ 'Idempotency-Key': 'inspect-key' }),
        timeout: 180_000,
      },
      {
        url: '/api/downloads',
        method: 'POST',
        headers: expect.objectContaining({ 'Idempotency-Key': 'download-key' }),
      },
    ]);
    expect(httpRequests()[1]?.data).toEqual({
      inspection_id: inspection.id,
      format_id: inspection.formats[0].id,
    });
    expect(httpRequests()[0]?.data).toEqual({
      source: { kind: 'public_url', url: 'https://media.example/owned' },
    });
  });

  it('uses owner-scoped article discovery and item inspection contracts', async () => {
    mockHttpResponses(sourceDiscovery, inspection);

    await createSourceDiscovery(
      'https://mp.weixin.qq.com/s/article_123',
      'discover-key',
    );
    await inspectDiscoveredItem(
      sourceDiscovery.id,
      sourceDiscovery.items[0].item_ref,
      'inspect-item-key',
    );

    expect(httpRequests()).toMatchObject([
      {
        url: '/api/source-discoveries',
        method: 'POST',
        headers: { 'Idempotency-Key': 'discover-key' },
      },
      {
        url: '/api/inspections',
        method: 'POST',
        headers: { 'Idempotency-Key': 'inspect-item-key' },
      },
    ]);
  });

  it('covers inspection, download, cancel, file and health endpoints', async () => {
    mockHttpResponses(
      inspection,
      job('running'),
      job('cancelled'),
      {
        url: 'https://objects.example/token',
        expires_at: '2026-08-06T10:05:00Z',
      },
      { status: 'ok' },
      { status: 'ok', service: 'api' },
    );
    await getInspection(inspection.id);
    await getDownload(job().id);
    await cancelDownload(job().id);
    await issueDownloadUrl(job().id);
    await getLiveness();
    await getReadiness();

    expect(httpRequests().map(({ url }) => url)).toEqual([
      `/api/inspections/${inspection.id}`,
      `/api/downloads/${job().id}`,
      `/api/downloads/${job().id}/cancel`,
      `/api/downloads/${job().id}/download-url`,
      '/health/live',
      '/health/ready',
    ]);
    expect(httpRequests()[3]).toMatchObject({
      headers: { 'X-FrameFetch-Download-Client': 'local-web' },
    });
  });

  it('forwards typed pagination and filters to the download history endpoint', async () => {
    const history = {
      items: [],
      page: 2,
      page_size: 20,
      summary: { active: 1, failed: 2, succeeded: 10, total: 41 },
      total: 41,
    };
    mockHttpResponses(history);

    await expect(
      getDownloadHistory({
        page: 2,
        page_size: 20,
        search: 'Owned video',
        status: 'succeeded',
      }),
    ).resolves.toEqual(history);
    expect(httpRequests()[0]).toMatchObject({
      method: 'GET',
      params: {
        page: 2,
        page_size: 20,
        search: 'Owned video',
        status: 'succeeded',
      },
      url: '/api/downloads/history',
    });
  });

  it('uses owner-scoped screenplay document list and detail endpoints', async () => {
    mockHttpResponses(screenplayDocumentPage(), screenplayDocument());

    await expect(
      listScreenplayDocuments({ page: 2, page_size: 20 }),
    ).resolves.toEqual(screenplayDocumentPage());
    await expect(getScreenplayDocument(documentId)).resolves.toEqual(
      screenplayDocument(),
    );

    expect(httpRequests()).toMatchObject([
      {
        method: 'GET',
        params: { page: 2, page_size: 20 },
        url: '/api/documents',
      },
      { method: 'GET', url: `/api/documents/${documentId}` },
    ]);
  });

  it('loads administrator download analytics for the selected period', async () => {
    const result = {
      period_days: 30,
      start: '2026-07-12',
      end: '2026-08-10',
      summary: {
        total: 0,
        succeeded: 0,
        failed: 0,
        cancelled: 0,
        active: 0,
        unique_users: 0,
        downloaded_bytes: 0,
        average_duration_seconds: 0,
        success_rate: 0,
      },
      daily: [],
      sources: [],
    };
    mockHttpResponses(result);

    await expect(getAdminDownloadAnalytics(30)).resolves.toEqual(result);
    expect(httpRequests()[0]).toMatchObject({
      method: 'GET',
      params: { days: 30 },
      url: '/api/admin/downloads/analytics',
    });
  });

  it('creates, queries and cancels analysis resources', async () => {
    mockHttpResponses(
      analysisJob(),
      analysisJob('running'),
      analysisJob('cancelled'),
    );
    await createAnalysis(
      job().id,
      {
        skill_id: 'highlights',
        output_language: 'en-US',
        custom_prompt: 'Focus on product reveals.',
      },
      'analysis-key',
    );
    await getAnalysis(analysisJob().id);
    await cancelAnalysis(analysisJob().id);

    expect(httpRequests()).toMatchObject([
      { url: `/api/downloads/${job().id}/analyses`, method: 'POST' },
      { url: `/api/analyses/${analysisJob().id}`, method: 'GET' },
      { url: `/api/analyses/${analysisJob().id}/cancel`, method: 'POST' },
    ]);
    expect(httpRequests()[0]?.data).toEqual({
      skill_id: 'highlights',
      output_language: 'en-US',
      custom_prompt: 'Focus on product reveals.',
    });
  });

  it('lists server-defined analysis skills', async () => {
    mockHttpResponses(analysisSkills);

    await expect(listAnalysisSkills()).resolves.toEqual(analysisSkills);
    expect(httpRequests()[0]).toMatchObject({
      url: '/api/analysis-skills',
      method: 'GET',
      params: { input_kind: 'video' },
    });
  });

  it('covers profile and administrator user management endpoints', async () => {
    const managedUser = {
      id: '11111111-1111-4111-8111-111111111111',
      username: 'video_user',
      email: 'user@example.com',
      role: 'user' as const,
      is_active: true,
      created_at: '2026-08-09T10:00:00Z',
      updated_at: '2026-08-09T10:00:00Z',
    };
    mockHttpResponses(
      managedUser,
      { items: [managedUser], page: 1, page_size: 20, total: 1 },
      { ...managedUser, role: 'admin' },
    );

    await updateCurrentUser({ username: 'video_user' });
    await listUsers({ page: 1, page_size: 20, role: 'user' });
    await updateUserAccess(managedUser.id, { role: 'admin' });

    expect(httpRequests()).toMatchObject([
      {
        url: '/api/users/me',
        method: 'PATCH',
        data: { username: 'video_user' },
      },
      {
        url: '/api/admin/users',
        method: 'GET',
        params: { page: 1, page_size: 20, role: 'user' },
      },
      {
        url: `/api/admin/users/${managedUser.id}`,
        method: 'PATCH',
        data: { role: 'admin' },
      },
    ]);
  });

  it('covers administrator platform catalog endpoints', async () => {
    const entry = {
      key: 'youtube',
      display_name: 'YouTube',
      sort_order: 10,
      is_visible: true,
      system_registered: true,
      system_status: 'verified' as const,
      created_at: '2026-08-12T10:00:00Z',
      updated_at: '2026-08-12T10:00:00Z',
    };
    mockHttpResponses(
      { items: [entry] },
      entry,
      { ...entry, display_name: 'YouTube Video' },
      undefined,
    );

    await listProviderCatalogEntries();
    await createProviderCatalogEntry({
      key: entry.key,
      display_name: entry.display_name,
      sort_order: entry.sort_order,
      is_visible: entry.is_visible,
    });
    await updateProviderCatalogEntry(entry.key, {
      display_name: 'YouTube Video',
    });
    await deleteProviderCatalogEntry(entry.key);

    expect(httpRequests().slice(-4)).toMatchObject([
      { url: '/api/admin/providers', method: 'GET' },
      {
        url: '/api/admin/providers',
        method: 'POST',
        data: {
          key: 'youtube',
          display_name: 'YouTube',
          sort_order: 10,
          is_visible: true,
        },
      },
      {
        url: '/api/admin/providers/youtube',
        method: 'PATCH',
        data: { display_name: 'YouTube Video' },
      },
      { url: '/api/admin/providers/youtube', method: 'DELETE' },
    ]);
  });
});
