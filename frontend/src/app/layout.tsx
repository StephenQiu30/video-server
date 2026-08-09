import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import Script from 'next/script';
import type { ReactNode } from 'react';

import { AppShell } from '@/components/app-shell';
import { AuthProvider } from '@/components/auth-provider';
import { ThemeInitializer } from '@/components/theme-toggle';
import { TooltipProvider } from '@/components/ui/tooltip';

import './globals.css';

const themeScript = `(function(){try{var stored=localStorage.getItem('framegrab-theme');var dark=stored?stored==='dark':matchMedia('(prefers-color-scheme: dark)').matches;document.documentElement.classList.toggle('dark',dark);document.documentElement.style.colorScheme=dark?'dark':'light';}catch(error){}})();`;

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: {
    default: '帧取 · 公开视频下载工具',
    template: '%s · 帧取',
  },
  description: '解析你有权处理的公开视频，选择格式并安全下载。',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      className={`${geistSans.variable} ${geistMono.variable}`}
      lang="zh-CN"
      suppressHydrationWarning
    >
      <head>
        <Script id="framegrab-theme" strategy="beforeInteractive">
          {themeScript}
        </Script>
      </head>
      <body>
        <ThemeInitializer />
        <AuthProvider>
          <TooltipProvider delayDuration={300}>
            <AppShell>{children}</AppShell>
          </TooltipProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
