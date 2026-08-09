'use client';

import { MoonIcon, SunIcon } from '@phosphor-icons/react';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';

const THEME_KEY = 'framegrab-theme';

export function ThemeInitializer() {
  useEffect(() => {
    setTheme(readPreferredTheme());
  }, []);

  return null;
}

export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const shouldUseDark = readPreferredTheme();
    setTheme(shouldUseDark);
    setDark(shouldUseDark);
  }, []);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    setTheme(next);
    window.localStorage.setItem(THEME_KEY, next ? 'dark' : 'light');
  }

  return (
    <Button
      aria-label={dark ? '切换到浅色模式' : '切换到深色模式'}
      className="size-10 rounded-full"
      onClick={toggleTheme}
      size="icon"
      variant="ghost"
    >
      {dark ? <MoonIcon aria-hidden /> : <SunIcon aria-hidden />}
    </Button>
  );
}

function readPreferredTheme() {
  const stored = window.localStorage.getItem(THEME_KEY);
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  return stored ? stored === 'dark' : prefersDark;
}

function setTheme(dark: boolean) {
  document.documentElement.classList.toggle('dark', dark);
  document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
}
