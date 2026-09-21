import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const session = vi.hoisted(() => ({ names: new Set<string>() }));
vi.mock('next/headers', () => ({
  cookies: async () => ({ has: (name: string) => session.names.has(name) }),
}));
vi.mock('@/components/auth/auth-provider', () => ({
  useAuth: () => ({ loading: true, user: undefined }),
}));
vi.mock('@/components/intake/workspace-home', () => ({
  WorkspaceHome: () => <div>Private workspace</div>,
}));

beforeEach(() => {
  session.names.clear();
  vi.resetModules();
  vi.stubEnv('SITE_INDEXABLE', 'true');
  vi.stubEnv('SITE_URL', 'https://framefetch.example');
});
afterEach(() => vi.unstubAllEnvs());

async function renderHome() {
  const { default: HomePage, generateMetadata } = await import('@/app/page');
  const html = renderToStaticMarkup(await HomePage());
  const document = new DOMParser().parseFromString(html, 'text/html');
  return { document, metadata: await generateMetadata() };
}

describe('anonymous homepage server rendering', () => {
  it('includes visible text and matching JSON-LD before client auth resolves', async () => {
    const { document, metadata } = await renderHome();
    expect(document.querySelectorAll('h1')).toHaveLength(1);
    expect(document.querySelector('[data-home-view="public"]')).not.toBeNull();
    expect(document.querySelector('[role="status"]')).toBeNull();
    const graph = JSON.parse(
      document.querySelector('script[type="application/ld+json"]')
        ?.textContent ?? '',
    );
    const faq = graph['@graph'].find(
      (item: Record<string, unknown>) => item['@type'] === 'FAQPage',
    );
    expect(faq.mainEntity).toHaveLength(6);
    for (const item of faq.mainEntity) {
      const id = new URL(item['@id']).hash.slice(1);
      const visible = document.getElementById(id);
      expect(visible?.textContent).toContain(item.name);
      expect(visible?.textContent).toContain(item.acceptedAnswer.text);
    }
    const software = graph['@graph'].find(
      (item: Record<string, unknown>) =>
        item['@type'] === 'SoftwareApplication',
    );
    expect(software).not.toHaveProperty('offers');
    expect(software).not.toHaveProperty('aggregateRating');
    expect(metadata.robots).toMatchObject({ index: true });
  });

  it.each(['video_access_token', 'video_refresh_token'])(
    'does not render promotional content with %s',
    async (cookie) => {
      session.names.add(cookie);
      const { document, metadata } = await renderHome();
      expect(
        document.querySelector('script[type="application/ld+json"]'),
      ).toBeNull();
      expect(document.querySelector('h1')).toBeNull();
      expect(document.querySelector('[role="status"]')).not.toBeNull();
      expect(metadata.robots).toMatchObject({ index: false, nosnippet: true });
      expect(metadata.alternates).toBeUndefined();
    },
  );

  it('respects custom cookie names', async () => {
    vi.stubEnv('AUTH_ACCESS_COOKIE_NAME', 'custom_access');
    session.names.add('custom_access');
    const { metadata } = await renderHome();
    expect(metadata.robots).toMatchObject({ index: false });
  });
});
