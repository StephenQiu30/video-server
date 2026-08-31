'use client';

import { MoonIcon, SunIcon } from '@phosphor-icons/react';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';

export function ThemeToggle() {
  const { setTheme, theme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const dark = mounted && theme === 'dark';

  return (
    <Button
      aria-label={dark ? '切换到浅色主题' : '切换到深色主题'}
      className="size-11 text-foreground"
      onClick={() => setTheme(dark ? 'light' : 'dark')}
      size="icon-lg"
      variant="ghost"
    >
      {dark ? (
        <SunIcon aria-hidden className="size-5" />
      ) : (
        <MoonIcon aria-hidden className="size-5" />
      )}
    </Button>
  );
}
