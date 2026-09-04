'use client';

import { CheckCircle, FloppyDisk, WarningCircle } from '@phosphor-icons/react';
import { type FormEvent, useEffect, useState } from 'react';
import { ReadOnlyField } from '@/components/account/read-only-field';
import { useAuth } from '@/components/auth/auth-provider';
import { BackLink } from '@/components/layout/back-link';
import { PageHeader } from '@/components/layout/page-header';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import {
  normalizeUsername,
  USERNAME_HELP,
  usernameLength,
  validateUsername,
} from '@/lib/username';
import { displayError, updateCurrentUser } from '@/services/users';

type Notice = { kind: 'error' | 'success'; text: string } | null;

export function AccountView() {
  const { user, loading, setUser, refreshUser } = useAuth();
  const [username, setUsername] = useState(user?.username ?? '');
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  useEffect(() => setUsername(user?.username ?? ''), [user?.username]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = normalizeUsername(username);
    const validationError = validateUsername(value);
    if (validationError) {
      setNotice({
        kind: 'error',
        text:
          validationError === 'unsupported_characters'
            ? '用户名仅支持字母、数字、中文以及 _-. 字符。'
            : '用户名长度需要在 2–32 个字符之间。',
      });
      return;
    }
    setSaving(true);
    setNotice(null);
    try {
      const updated = await updateCurrentUser({ username: value });
      setUser(updated);
      setUsername(updated.username);
      setNotice({ kind: 'success', text: '个人资料已更新。' });
    } catch (error) {
      setNotice({ kind: 'error', text: displayError(error) });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <section aria-label="正在加载个人资料" className="space-y-8">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-24 w-full max-w-2xl" />
        <div className="grid gap-12 pt-4 lg:grid-cols-[minmax(220px,0.7fr)_minmax(0,1.3fr)] lg:gap-20">
          <Skeleton className="h-32 w-full max-w-xs" />
          <div className="space-y-6">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </div>
      </section>
    );
  }

  if (!user) {
    return (
      <Alert variant="destructive" className="max-w-2xl">
        <WarningCircle />
        <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
          登录状态已失效，请重新检查账户状态。
          <Button
            variant="outline"
            size="sm"
            onClick={() => void refreshUser()}
          >
            重新检查
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  const unchanged = normalizeUsername(username) === user.username;
  const role = user.role === 'admin' ? '管理员' : '普通用户';
  const initials = user.username.trim().slice(0, 2).toUpperCase();

  return (
    <section>
      <BackLink className="mb-4" fallbackHref="/" />
      <PageHeader
        description="管理公开用户名，并查看不会随任务变化的账户身份信息。"
        title="个人资料"
      />

      <form
        className="mt-14 grid gap-12 sm:mt-16 lg:grid-cols-[minmax(220px,0.7fr)_minmax(0,1.3fr)] lg:gap-20"
        onSubmit={submit}
      >
        <aside>
          <h2 className="text-sm font-medium">当前身份</h2>
          <div className="mt-5 flex items-center gap-4">
            <Avatar aria-hidden className="size-14">
              <AvatarFallback className="bg-muted text-lg font-medium text-foreground">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <p className="truncate text-lg font-medium tracking-[-0.02em]">
                {user.username}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">{role}</p>
            </div>
          </div>
          <p className="mt-7 max-w-xs text-sm leading-6 text-muted-foreground">
            用户名会显示在导航与任务记录中；登录邮箱和账户身份由系统策略管理。
          </p>
        </aside>

        <div>
          <h2 className="mb-6 text-sm font-medium">资料字段</h2>
          <FieldGroup className="gap-8">
            <Field>
              <div className="flex items-center justify-between gap-3">
                <FieldLabel htmlFor="username">用户名</FieldLabel>
                <span className="text-xs text-muted-foreground tabular-nums">
                  {usernameLength(username)}/32
                </span>
              </div>
              <Input
                aria-describedby="username-help"
                id="username"
                onChange={(event) => {
                  setUsername(event.target.value);
                  setNotice(null);
                }}
                required
                value={username}
              />
              <FieldDescription id="username-help">
                {USERNAME_HELP} 将显示在导航和任务记录中。
              </FieldDescription>
            </Field>
            <div className="grid gap-6 sm:grid-cols-2">
              <ReadOnlyField
                description="用于登录账户，暂不支持在此修改。"
                id="email"
                label="登录邮箱"
                value={user.email}
              />
              <ReadOnlyField
                description="由账户权限策略分配。"
                id="role"
                label="账户身份"
                value={role}
              />
            </div>
            {notice ? (
              <Alert
                variant={notice.kind === 'success' ? 'success' : 'destructive'}
              >
                {notice.kind === 'success' ? (
                  <CheckCircle aria-hidden />
                ) : (
                  <WarningCircle aria-hidden />
                )}
                <AlertDescription>{notice.text}</AlertDescription>
              </Alert>
            ) : null}
          </FieldGroup>
          <div className="mt-9 flex justify-start">
            <Button disabled={saving || unchanged} size="lg" type="submit">
              {saving ? (
                <Spinner aria-hidden role="presentation" />
              ) : (
                <FloppyDisk aria-hidden />
              )}
              {saving ? '正在保存' : '保存资料'}
            </Button>
          </div>
        </div>
      </form>
    </section>
  );
}
