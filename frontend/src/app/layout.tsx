import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import type { ReactNode } from 'react';
import { AuthProvider } from '@/components/auth/auth-provider';
import { AppShell } from '@/components/layout/app-shell';
import { ThemeProvider } from '@/components/layout/theme-provider';
import { TooltipProvider } from '@/components/ui/tooltip';
import { siteConfig, siteUrl } from '@/lib/site';

import '@vidstack/react/player/styles/default/theme.css';
import '@vidstack/react/player/styles/default/layouts/video.css';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  metadataBase: siteUrl,
  title: {
    default: siteConfig.title,
    template: '%s · 帧取',
  },
  applicationName: siteConfig.name,
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
  icons: {
    icon: [{ url: '/logo.svg', type: 'image/svg+xml' }],
    apple: [{ url: '/logo.png', sizes: '1024x1024', type: 'image/png' }],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: siteConfig.shortName,
  },
  robots: {
    index: false,
    follow: false,
    noarchive: true,
    nosnippet: true,
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      className={`${geistSans.variable} ${geistMono.variable}`}
      lang="zh-CN"
      suppressHydrationWarning
    >
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          disableTransitionOnChange
          enableSystem={false}
          storageKey="framegrab-theme"
          themes={['light', 'dark']}
        >
          <AuthProvider>
            <TooltipProvider delayDuration={300}>
              <AppShell>{children}</AppShell>
            </TooltipProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
