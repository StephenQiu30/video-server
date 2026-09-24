'use client';

import {
  FileTextIcon,
  FileVideoIcon,
  LinkSimpleIcon,
  MagnifyingGlassIcon,
} from '@phosphor-icons/react';
import { usePathname, useRouter } from 'next/navigation';
import { type ClipboardEvent, useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/components/auth/auth-provider';
import type { IntakeMode } from '@/components/intake/content-intake-hero';
import { useIntakeDraft } from '@/components/intake/intake-draft-provider';
import {
  hasPublicInput,
  PUBLIC_INPUT_REQUIRED,
} from '@/components/intake/public-input';
import { markNavigationPush } from '@/components/layout/navigation-history';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandDialog,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
} from '@/components/ui/command';
import { FieldError } from '@/components/ui/field';
import { Kbd } from '@/components/ui/kbd';

export function QuickParseDialog() {
  const { user } = useAuth();
  const { input, requestQuickParse, setMode } = useIntakeDraft();
  const pathname = usePathname() ?? '/';
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState('');
  const [invalid, setInvalid] = useState(false);

  const openDialog = useCallback(() => {
    setValue(input);
    setInvalid(false);
    setOpen(true);
  }, [input]);

  useEffect(() => {
    if (!user) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (
        event.key.toLowerCase() !== 'k' ||
        (!event.metaKey && !event.ctrlKey) ||
        event.altKey ||
        event.shiftKey ||
        event.repeat ||
        event.isComposing
      )
        return;
      event.preventDefault();
      if (open) setOpen(false);
      else openDialog();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [user, open, openDialog]);

  function submit() {
    if (!hasPublicInput(value)) {
      setInvalid(true);
      return;
    }
    requestQuickParse(value);
    setOpen(false);
    if (pathname !== '/') {
      markNavigationPush('/');
      router.push('/');
    }
  }

  function selectUpload(mode: Extract<IntakeMode, 'video' | 'screenplay'>) {
    setMode(mode);
    setOpen(false);
    if (pathname !== '/') {
      markNavigationPush('/');
      router.push('/');
    }
  }

  function pasteShareText(event: ClipboardEvent<HTMLInputElement>) {
    const pasted = event.clipboardData.getData('text');
    if (!/[\r\n]/.test(pasted)) return;
    event.preventDefault();
    const target = event.currentTarget;
    const start = target.selectionStart ?? value.length;
    const end = target.selectionEnd ?? start;
    setValue(
      `${value.slice(0, start)}${pasted.replace(/\s+/g, ' ')}${value.slice(end)}`.slice(
        0,
        4096,
      ),
    );
    setInvalid(false);
  }

  if (!user) return null;

  return (
    <>
      <Button
        aria-label="快速操作（⌘K）"
        className="xl:hidden"
        onClick={openDialog}
        size="icon-lg"
        variant="ghost"
      >
        <MagnifyingGlassIcon aria-hidden />
      </Button>
      <Button
        className="hidden xl:inline-flex"
        onClick={openDialog}
        size="sm"
        variant="outline"
      >
        <MagnifyingGlassIcon aria-hidden data-icon="inline-start" />
        快速操作
        <Kbd>⌘ K</Kbd>
      </Button>
      <CommandDialog
        className="sm:max-w-2xl"
        description="解析公开链接，或选择上传本地视频与剧本文档。"
        onOpenChange={setOpen}
        open={open}
        title="快速操作"
      >
        <Command label="链接或操作" shouldFilter={false}>
          <CommandInput
            aria-describedby={invalid ? 'quick-parse-error' : undefined}
            aria-invalid={invalid ? true : undefined}
            aria-label="链接或操作"
            maxLength={4096}
            onPaste={pasteShareText}
            onValueChange={(nextValue) => {
              setValue(nextValue);
              setInvalid(false);
            }}
            placeholder="粘贴媒体链接，或选择下方操作…"
            value={value}
          />
          <CommandList>
            <CommandGroup heading="选择操作">
              <CommandItem onSelect={submit} value="解析链接">
                <LinkSimpleIcon aria-hidden />
                解析链接
                <CommandShortcut>↵</CommandShortcut>
              </CommandItem>
              <CommandItem
                onSelect={() => selectUpload('video')}
                value="上传本地视频"
              >
                <FileVideoIcon aria-hidden />
                上传本地视频
              </CommandItem>
              <CommandItem
                onSelect={() => selectUpload('screenplay')}
                value="上传剧本文档"
              >
                <FileTextIcon aria-hidden />
                上传剧本文档
              </CommandItem>
            </CommandGroup>
          </CommandList>
          {invalid ? (
            <FieldError id="quick-parse-error">
              {PUBLIC_INPUT_REQUIRED}
            </FieldError>
          ) : null}
        </Command>
      </CommandDialog>
    </>
  );
}
