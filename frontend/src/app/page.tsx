import type { Metadata } from 'next';
import { cookies } from 'next/headers';

import { HomeExperience } from '@/components/intake/home-experience';
import { PublicHome } from '@/components/intake/public-home';
import { absoluteUrl, siteConfig } from '@/lib/site';

const publicHomeMetadata: Metadata = {
  applicationName: siteConfig.name,
  title: {
    absolute: siteConfig.title,
  },
  description: siteConfig.description,
  keywords: [
    '帧取',
    'FrameFetch',
    '开源视频下载',
    '自托管视频下载',
    'AI 视频分析',
    '剧本分析',
    'video downloader',
    'self-hosted',
    'FastAPI',
    'Next.js',
    'yt-dlp',
    'FFmpeg',
  ],
  authors: [{ name: 'FrameFetch contributors', url: siteConfig.repositoryUrl }],
  creator: 'FrameFetch contributors',
  publisher: 'FrameFetch',
  category: 'technology',
  referrer: 'strict-origin-when-cross-origin',
  alternates: {
    canonical: '/',
  },
  openGraph: {
    type: 'website',
    locale: 'zh_CN',
    url: '/',
    siteName: siteConfig.name,
    title: siteConfig.title,
    description: siteConfig.description,
    images: [
      {
        url: '/opengraph-image/',
        width: 1200,
        height: 630,
        alt: 'FrameFetch — self-hosted media workflow and AI analysis',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: siteConfig.title,
    description: siteConfig.englishDescription,
    images: ['/opengraph-image/'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-image-preview': 'large',
      'max-snippet': -1,
      'max-video-preview': -1,
    },
  },
};

const privateHomeMetadata: Metadata = {
  title: '工作区',
  robots: {
    index: false,
    follow: false,
    noarchive: true,
    nosnippet: true,
  },
};

const accessCookieName =
  process.env.AUTH_ACCESS_COOKIE_NAME ?? 'video_access_token';
const refreshCookieName =
  process.env.AUTH_REFRESH_COOKIE_NAME ?? 'video_refresh_token';

async function hasBrowserSession() {
  const cookieStore = await cookies();
  return (
    cookieStore.has(accessCookieName) || cookieStore.has(refreshCookieName)
  );
}

export async function generateMetadata(): Promise<Metadata> {
  return (await hasBrowserSession()) ? privateHomeMetadata : publicHomeMetadata;
}

const structuredData = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'WebSite',
      '@id': absoluteUrl('/#website'),
      url: absoluteUrl('/'),
      name: siteConfig.name,
      alternateName: 'FrameFetch',
      description: siteConfig.description,
      inLanguage: ['zh-CN', 'en'],
    },
    {
      '@type': 'SoftwareApplication',
      '@id': absoluteUrl('/#software'),
      name: siteConfig.name,
      alternateName: 'FrameFetch',
      description: siteConfig.englishDescription,
      url: absoluteUrl('/'),
      codeRepository: siteConfig.repositoryUrl,
      license: siteConfig.licenseUrl,
      applicationCategory: 'MultimediaApplication',
      applicationSubCategory: 'Media workflow and video analysis',
      operatingSystem: 'Web, Docker, Linux, macOS, Windows',
      isAccessibleForFree: true,
      offers: {
        '@type': 'Offer',
        price: '0',
        priceCurrency: 'USD',
      },
    },
    {
      '@type': 'SoftwareSourceCode',
      name: 'FrameFetch source code',
      description: siteConfig.englishDescription,
      codeRepository: siteConfig.repositoryUrl,
      license: siteConfig.licenseUrl,
      programmingLanguage: ['Python', 'TypeScript'],
      runtimePlatform: ['Docker', 'Node.js', 'Python'],
    },
  ],
};

export default async function HomePage() {
  const privateHome = await hasBrowserSession();

  return (
    <>
      {!privateHome ? (
        <script type="application/ld+json">
          {JSON.stringify(structuredData).replace(/</g, '\\u003c')}
        </script>
      ) : null}
      <HomeExperience publicHome={<PublicHome />} />
    </>
  );
}
