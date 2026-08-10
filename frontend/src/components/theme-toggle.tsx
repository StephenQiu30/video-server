'use client';

import { MoonIcon, SunIcon } from '@phosphor-icons/react';
import { useTheme } from 'next-themes';

import { Button } from '@/components/ui/button';

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const dark = resolvedTheme === 'dark';

  return (
    <Button
      aria-label="切换颜色主题"
      className="size-11 rounded-full [&_svg]:size-5"
      onClick={() => setTheme(dark ? 'light' : 'dark')}
      size="icon"
      variant="ghost"
    >
      <SunIcon aria-hidden className="dark:hidden" />
      <MoonIcon aria-hidden className="hidden dark:block" />
    </Button>
  );
}
