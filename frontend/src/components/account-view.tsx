'use client';

import {
  CheckCircle,
  EnvelopeSimple,
  FloppyDisk,
  ShieldCheck,
  UserCircle,
  WarningCircle,
} from '@phosphor-icons/react';
import { type FormEvent, useEffect, useState } from 'react';

import { ReadOnlyField } from '@/components/app-shell';
import { useAuth } from '@/components/auth-provider';
import { PageHeader } from '@/components/page-header';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from '@/components/ui/card';
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
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
    const value = username.trim();
    if (value.length < 2 || value.length > 32) {
      setNotice({ kind: 'error', text: '用户名长度需要在 2–32 个字符之间。' });
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
      <section className="max-w-3xl space-y-6" aria-label="正在加载个人资料">
        <Skeleton className="h-16 w-64 max-w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-24 w-full" />
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

  const unchanged = username.trim() === user.username;
  const role = user.role === 'admin' ? '管理员' : '普通用户';
  const initials = user.username.trim().slice(0, 2).toUpperCase();

  return (
    <section>
      <Card className="gap-0 rounded-none bg-transparent py-0 shadow-none ring-0">
        <CardHeader className="rounded-t-none px-0 py-0">
          <PageHeader
            action={
              <Avatar aria-hidden className="size-12">
                <AvatarFallback className="bg-muted text-base font-medium text-foreground">
                  {initials}
                </AvatarFallback>
              </Avatar>
            }
            description="管理公开用户名并查看账户身份信息。"
            title="个人资料"
          />
        </CardHeader>
        <form className="mt-10 max-w-3xl" onSubmit={submit}>
          <CardContent className="px-0 py-0">
            <FieldGroup className="gap-7">
              <Field>
                <div className="flex items-center justify-between gap-3">
                  <FieldLabel htmlFor="username">
                    <UserCircle aria-hidden size={17} />
                    用户名
                  </FieldLabel>
                  <span className="font-mono text-xs text-muted-foreground tabular-nums">
                    {username.length}/32
                  </span>
                </div>
                <Input
                  aria-describedby="username-help"
                  id="username"
                  maxLength={32}
                  minLength={2}
                  onChange={(event) => {
                    setUsername(event.target.value);
                    setNotice(null);
                  }}
                  required
                  value={username}
                />
                <FieldDescription id="username-help">
                  2–32 个字符，将显示在导航和任务记录中。
                </FieldDescription>
              </Field>
              <Separator />
              <div className="grid gap-6 sm:grid-cols-2">
                <ReadOnlyField
                  description="用于登录账户，暂不支持在此修改。"
                  icon={<EnvelopeSimple aria-hidden size={17} />}
                  id="email"
                  label="登录邮箱"
                  value={user.email}
                />
                <ReadOnlyField
                  description="由账户权限策略分配。"
                  icon={<ShieldCheck aria-hidden size={17} />}
                  id="role"
                  label="账户身份"
                  value={role}
                />
              </div>
              {notice ? (
                <Alert
                  variant={
                    notice.kind === 'success' ? 'success' : 'destructive'
                  }
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
          </CardContent>
          <CardFooter className="mt-8 justify-start rounded-b-none border-t-0 bg-transparent p-0">
            <Button disabled={saving || unchanged} size="lg" type="submit">
              {saving ? (
                <Spinner aria-hidden role="presentation" />
              ) : (
                <FloppyDisk aria-hidden />
              )}
              {saving ? '正在保存' : '保存资料'}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </section>
  );
}
