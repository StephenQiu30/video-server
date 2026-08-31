'use client';

import { DesktopIcon, MoonIcon, SunIcon } from '@phosphor-icons/react';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const themeOptions = [
  { icon: SunIcon, label: '浅色', value: 'light' },
  { icon: MoonIcon, label: '深色', value: 'dark' },
  { icon: DesktopIcon, label: '跟随系统', value: 'system' },
] as const;

type ThemeValue = (typeof themeOptions)[number]['value'];

function isThemeValue(value: string | undefined): value is ThemeValue {
  return themeOptions.some((option) => option.value === value);
}

export function ThemeMenu() {
  const { setTheme, theme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const currentTheme = mounted && isThemeValue(theme) ? theme : 'system';
  const currentOption =
    themeOptions.find((option) => option.value === currentTheme) ??
    themeOptions[2];
  const CurrentIcon = currentOption.icon;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          aria-label={`切换主题，当前：${currentOption.label}`}
          className="size-11 text-foreground"
          size="icon-lg"
          variant="ghost"
        >
          <CurrentIcon aria-hidden className="size-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        aria-label="主题设置"
        className="w-44"
        sideOffset={8}
      >
        <DropdownMenuLabel>主题</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuRadioGroup
          onValueChange={(value) => {
            if (isThemeValue(value)) setTheme(value);
          }}
          value={currentTheme}
        >
          {themeOptions.map((option) => {
            const Icon = option.icon;
            return (
              <DropdownMenuRadioItem key={option.value} value={option.value}>
                <Icon aria-hidden className="size-4" />
                {option.label}
              </DropdownMenuRadioItem>
            );
          })}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
