import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import manifest from '@/app/manifest';
import robots from '@/app/robots';
import sitemap from '@/app/sitemap';
import { canonicalSecureDeploymentRedirect, resolveSiteUrl } from '@/lib/site';

describe('public SEO metadata', () => {
  it('publishes crawl discovery files for the public landing page', () => {
    const robotsFile = robots();
    const sitemapFile = sitemap();

    expect(robotsFile.rules).toMatchObject({
      userAgent: '*',
      allow: '/',
      disallow: ['/api/', '/health/'],
    });
    expect(robotsFile.sitemap).toMatch(/\/sitemap\.xml$/);
    expect(sitemapFile).toHaveLength(1);
    expect(sitemapFile[0]).toMatchObject({
      changeFrequency: 'weekly',
      priority: 1,
    });
  });

  it('rejects an explicitly invalid canonical origin', () => {
    expect(resolveSiteUrl(undefined).origin).toBe('http://127.0.0.1:8101');
    expect(resolveSiteUrl('https://framefetch.example/path').toString()).toBe(
      'https://framefetch.example/',
    );
    expect(() => resolveSiteUrl('framefetch.example')).toThrow(
      'SITE_URL must be an absolute HTTP(S) URL',
    );
    expect(() => resolveSiteUrl('ftp://framefetch.example')).toThrow(
      'SITE_URL must be an absolute HTTP(S) URL',
    );
  });

  it('redirects production UI requests to the configured HTTPS origin', () => {
    const redirect = canonicalSecureDeploymentRedirect(
      new URL('http://127.0.0.1:8101/user/login?redirect=%2Fhistory'),
      '127.0.0.1:8101',
      'http',
      'https://framefetch.example',
      true,
    );

    expect(redirect?.toString()).toBe(
      'https://framefetch.example/user/login?redirect=%2Fhistory',
    );
    expect(
      canonicalSecureDeploymentRedirect(
        new URL('https://framefetch.example/user/login'),
        'framefetch.example',
        'https',
        'https://framefetch.example',
        true,
      ),
    ).toBeNull();
    expect(
      canonicalSecureDeploymentRedirect(
        new URL('http://framefetch.example/user/login?redirect=%2Fhistory'),
        'framefetch.example',
        'http',
        'https://framefetch.example',
        true,
      )?.toString(),
    ).toBe('https://framefetch.example/user/login?redirect=%2Fhistory');
    expect(
      canonicalSecureDeploymentRedirect(
        new URL('http://frontend:8101/user/login'),
        'framefetch.example',
        'https',
        'https://framefetch.example',
        true,
      ),
    ).toBeNull();
  });

  it('keeps local development on HTTP and rejects insecure production origins', () => {
    expect(
      canonicalSecureDeploymentRedirect(
        new URL('http://127.0.0.1:8101/user/login'),
        '127.0.0.1:8101',
        null,
        undefined,
        false,
      ),
    ).toBeNull();
    expect(() =>
      canonicalSecureDeploymentRedirect(
        new URL('http://127.0.0.1:8101/user/login'),
        '127.0.0.1:8101',
        'http',
        'http://127.0.0.1:8101',
        true,
      ),
    ).toThrow('SITE_URL must use HTTPS in secure deployments');
  });

  it('describes an installable FrameFetch web application', () => {
    expect(manifest()).toMatchObject({
      short_name: '帧取',
      start_url: '/',
      scope: '/',
      display: 'standalone',
    });
  });

  it('indexes only the public root and exposes truthful software JSON-LD', () => {
    const rootLayout = readFileSync(
      resolve(process.cwd(), 'src/app/layout.tsx'),
      'utf8',
    );
    const homePage = readFileSync(
      resolve(process.cwd(), 'src/app/page.tsx'),
      'utf8',
    );

    expect(rootLayout).toContain('index: false');
    expect(homePage).toContain('index: true');
    expect(homePage).toContain("'@type': 'SoftwareApplication'");
    expect(homePage).toContain('codeRepository: siteConfig.repositoryUrl');
    expect(homePage).toContain("price: '0'");
  });

  it('keeps anonymous session discovery on the public landing page', () => {
    const authService = readFileSync(
      resolve(process.cwd(), 'src/services/auth.ts'),
      'utf8',
    );
    const requestClient = readFileSync(
      resolve(process.cwd(), 'src/lib/request.ts'),
      'utf8',
    );

    expect(authService).toContain('skipAuthRedirect: true');
    expect(requestClient).toContain(
      'if (!config.skipAuthRedirect) redirectToLogin();',
    );
  });
});
