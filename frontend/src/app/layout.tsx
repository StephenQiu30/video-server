import { AntdRegistry } from '@ant-design/nextjs-registry';
import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';

import AppShell from '@/components/app-shell';

import './globals.css';

const geistSans = Geist({ subsets: ['latin'], variable: '--font-geist-sans' });
const geistMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-geist-mono',
});

export const metadata: Metadata = {
  title: { default: '帧取', template: '%s · 帧取' },
  description: '解析、下载并分析你有权处理的公开视频。',
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      className={`${geistSans.variable} ${geistMono.variable}`}
      lang="zh-CN"
    >
      <body>
        <AntdRegistry>
          <AppShell>{children}</AppShell>
        </AntdRegistry>
      </body>
    </html>
  );
}
