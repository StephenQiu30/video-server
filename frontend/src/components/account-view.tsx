'use client';

import {
  CheckCircle,
  EnvelopeSimple,
  FloppyDisk,
  ShieldCheck,
  SpinnerGap,
  UserCircle,
  WarningCircle,
} from '@phosphor-icons/react';
import { type FormEvent, useEffect, useState } from 'react';

import { useAuth } from '@/components/auth-provider';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
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
      <section
        className="mx-auto max-w-2xl space-y-6"
        aria-label="正在加载个人资料"
      >
        <Skeleton className="h-16 w-64" />
        <Skeleton className="h-44 w-full" />
        <Skeleton className="h-28 w-full" />
      </section>
    );
  }

  if (!user) {
    return (
      <Alert variant="destructive" className="mx-auto max-w-2xl">
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

  return (
    <section className="mx-auto max-w-2xl">
      <header className="flex items-start gap-4 border-b pb-7">
        <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-accent text-primary">
          <UserCircle size={27} weight="duotone" />
        </span>
        <div>
          <p className="text-sm font-medium text-primary">账户设置</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-[-0.025em]">
            个人资料
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            管理公开用户名并查看账户身份信息。
          </p>
        </div>
      </header>

      <form onSubmit={submit} className="space-y-7 py-7">
        <div className="space-y-2.5 border-b pb-7">
          <label
            htmlFor="username"
            className="flex items-center justify-between gap-3 text-sm font-medium"
          >
            <span className="flex items-center gap-2">
              <UserCircle size={17} />
              用户名
            </span>
            <span className="font-normal text-muted-foreground">
              {username.length}/32
            </span>
          </label>
          <Input
            id="username"
            value={username}
            minLength={2}
            maxLength={32}
            required
            aria-describedby="username-help"
            onChange={(event) => {
              setUsername(event.target.value);
              setNotice(null);
            }}
          />
          <p id="username-help" className="text-sm text-muted-foreground">
            2–32 个字符，将显示在导航和任务记录中。
          </p>
        </div>

        <div className="grid gap-5 border-b pb-7 sm:grid-cols-2">
          <div className="space-y-2.5">
            <label
              htmlFor="email"
              className="flex items-center gap-2 text-sm font-medium"
            >
              <EnvelopeSimple size={17} />
              登录邮箱
            </label>
            <Input
              id="email"
              value={user.email}
              readOnly
              aria-readonly="true"
              className="bg-muted/70 text-muted-foreground"
            />
          </div>
          <div className="space-y-2.5">
            <label
              htmlFor="role"
              className="flex items-center gap-2 text-sm font-medium"
            >
              <ShieldCheck size={17} />
              账户身份
            </label>
            <Input
              id="role"
              value={role}
              readOnly
              aria-readonly="true"
              className="bg-muted/70 text-muted-foreground"
            />
          </div>
        </div>

        {notice && (
          <Alert
            variant={notice.kind === 'success' ? 'success' : 'destructive'}
          >
            {notice.kind === 'success' ? <CheckCircle /> : <WarningCircle />}
            <AlertDescription>{notice.text}</AlertDescription>
          </Alert>
        )}

        <div className="flex justify-end">
          <Button type="submit" size="lg" disabled={saving || unchanged}>
            {saving ? <SpinnerGap className="animate-spin" /> : <FloppyDisk />}
            {saving ? '正在保存' : '保存资料'}
          </Button>
        </div>
      </form>
    </section>
  );
}
