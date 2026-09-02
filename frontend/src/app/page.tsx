import type { Metadata } from 'next';

import { HomeExperience } from '@/components/intake/home-experience';
import { PublicHome } from '@/components/intake/public-home';
import { absoluteUrl, siteConfig } from '@/lib/site';

export const metadata: Metadata = {
  title: {
    absolute: siteConfig.title,
  },
  description: siteConfig.description,
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

export default function HomePage() {
  return (
    <>
      <script type="application/ld+json">
        {JSON.stringify(structuredData).replace(/</g, '\\u003c')}
      </script>
      <HomeExperience publicHome={<PublicHome />} />
    </>
  );
}
