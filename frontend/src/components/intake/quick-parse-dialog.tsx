'use client';

import {
  BookOpenIcon,
  FileTextIcon,
  FileVideoIcon,
  LinkSimpleIcon,
  MagnifyingGlassIcon,
  SignInIcon,
} from '@phosphor-icons/react';
import { usePathname, useRouter } from 'next/navigation';
import {
  type ClipboardEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
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
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
} from '@/components/ui/command';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { FieldError } from '@/components/ui/field';
import { Kbd } from '@/components/ui/kbd';

export function QuickParseDialog() {
  const { user } = useAuth();
  const { input, requestQuickParse, setMode } = useIntakeDraft();
  const pathname = usePathname() ?? '/';
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const returnFocus = useRef<HTMLElement | null>(null);
  const [value, setValue] = useState('');
  const [invalid, setInvalid] = useState(false);

  const openDialog = useCallback(() => {
    returnFocus.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    setValue(input);
    setInvalid(false);
    setOpen(true);
  }, [input]);

  useEffect(() => {
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
  }, [open, openDialog]);

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

  return (
    <>
      <Button
        aria-haspopup="dialog"
        aria-keyshortcuts="Meta+K Control+K"
        aria-label="快捷操作"
        onClick={openDialog}
        size="sm"
        variant="ghost"
      >
        <MagnifyingGlassIcon aria-hidden data-icon="inline-start" />
        快捷操作
        <Kbd className="hidden sm:inline-flex">⌘ / Ctrl K</Kbd>
      </Button>
      <Dialog onOpenChange={setOpen} open={open}>
        <DialogContent
          className="max-h-[calc(100svh-2rem)] overflow-y-auto sm:max-w-2xl"
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            if (returnFocus.current?.isConnected)
              returnFocus.current.focus({ preventScroll: true });
          }}
        >
          <DialogHeader>
            <DialogTitle>快捷操作</DialogTitle>
            <DialogDescription>
              {user
                ? '解析公开链接，或上传本地视频与剧本文档。'
                : '登录后可解析链接、上传视频与剧本文档。'}
            </DialogDescription>
          </DialogHeader>
          <Command
            label="链接或操作"
            shouldFilter={false}
            tabIndex={user ? undefined : 0}
          >
            {user ? (
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
            ) : null}
            <CommandList>
              {user ? (
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
              ) : (
                <CommandGroup heading="开始使用">
                  <CommandItem
                    onSelect={() => {
                      setOpen(false);
                      const target = '/user/login?redirect=%2F';
                      markNavigationPush(target);
                      router.push(target);
                    }}
                    value="登录后使用"
                  >
                    <SignInIcon aria-hidden />
                    登录后使用
                  </CommandItem>
                  <CommandItem
                    onSelect={() => {
                      setOpen(false);
                      markNavigationPush('/guide/');
                      router.push('/guide/');
                    }}
                    value="使用指南"
                  >
                    <BookOpenIcon aria-hidden />
                    使用指南
                  </CommandItem>
                </CommandGroup>
              )}
            </CommandList>
            {invalid ? (
              <FieldError id="quick-parse-error">
                {PUBLIC_INPUT_REQUIRED}
              </FieldError>
            ) : null}
          </Command>
        </DialogContent>
      </Dialog>
    </>
  );
}
