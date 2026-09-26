'use client';

import { FloppyDisk, UploadSimpleIcon, XIcon } from '@phosphor-icons/react';
import {
  type ChangeEvent,
  type FormEvent,
  useEffect,
  useRef,
  useState,
} from 'react';
import { toast } from 'sonner';
import {
  deleteCurrentUserAvatar,
  updateCurrentUser,
  uploadCurrentUserAvatar,
} from '@/api/users';
import { ReadOnlyField } from '@/components/account/read-only-field';
import { useAuth } from '@/components/auth/auth-provider';
import { FeedbackNotice } from '@/components/layout/feedback-notice';
import { PageErrorNotice } from '@/components/layout/page-error-notice';
import { PageHeader } from '@/components/layout/page-header';
import { PageNavigation } from '@/components/layout/page-navigation';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field';
import { Form } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import { avatarUrl } from '@/lib/avatar';
import { displayError } from '@/lib/request-error';
import {
  normalizeUsername,
  USERNAME_HELP,
  usernameLength,
  validateUsername,
} from '@/lib/username';

type Notice = { text: string } | null;
const MAX_AVATAR_UPLOAD_BYTES = 4 * 1024 * 1024;
const AVATAR_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);

export function AccountView() {
  const { user, loading, setUser, refreshUser } = useAuth();
  const [username, setUsername] = useState(user?.username ?? '');
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const avatarInput = useRef<HTMLInputElement>(null);

  useEffect(() => setUsername(user?.username ?? ''), [user?.username]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = normalizeUsername(username);
    const validationError = validateUsername(value);
    if (validationError) {
      setNotice({
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
      toast.success('个人资料已更新。');
    } catch (error) {
      setNotice({ text: displayError(error) });
    } finally {
      setSaving(false);
    }
  }

  async function uploadAvatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (!AVATAR_TYPES.has(file.type)) {
      setAvatarError('请选择 JPEG、PNG 或 WebP 图片。');
      return;
    }
    if (file.size === 0 || file.size > MAX_AVATAR_UPLOAD_BYTES) {
      setAvatarError('头像文件不能超过 4 MB。');
      return;
    }
    setAvatarError(null);
    setAvatarBusy(true);
    try {
      const updated = await uploadCurrentUserAvatar(file);
      setUser(updated);
      toast.success('头像已更新。');
    } catch (error) {
      toast.error(displayError(error));
    } finally {
      setAvatarBusy(false);
    }
  }

  async function deleteAvatar() {
    setAvatarError(null);
    setAvatarBusy(true);
    try {
      const updated = await deleteCurrentUserAvatar();
      setUser(updated);
      toast.success('头像已移除。');
    } catch (error) {
      toast.error(displayError(error));
    } finally {
      setAvatarBusy(false);
    }
  }

  if (loading) {
    return (
      <div
        aria-label="正在加载个人资料"
        className="flex flex-col gap-8"
        role="status"
      >
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-24 w-full max-w-2xl" />
        <div className="grid gap-12 pt-4 lg:grid-cols-[minmax(220px,0.7fr)_minmax(0,1.3fr)] lg:gap-20">
          <Skeleton className="h-32 w-full max-w-xs" />
          <div className="flex flex-col gap-6">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <PageErrorNotice
        message="登录状态已失效，请重新检查账户状态。"
        onRetry={() => void refreshUser()}
        retryLabel="重新检查"
        title="暂时无法读取个人资料"
      />
    );
  }

  const unchanged = normalizeUsername(username) === user.username;
  const role = user.role === 'admin' ? '管理员' : '普通用户';
  const initials = user.username.trim().slice(0, 2).toUpperCase();

  return (
    <div>
      <PageNavigation fallbackHref="/" />
      <PageHeader
        description="管理公开用户名，并查看不会随任务变化的账户身份信息。"
        title="个人资料"
      />

      <Form
        className="mt-14 grid gap-12 sm:mt-16 lg:grid-cols-[minmax(220px,0.7fr)_minmax(0,1.3fr)] lg:gap-20"
        onSubmit={submit}
      >
        <aside>
          <h2 className="text-sm font-medium">当前身份</h2>
          <div className="mt-5 flex items-center gap-4">
            <Avatar aria-hidden className="size-14">
              <AvatarImage alt="" src={avatarUrl(user)} />
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <p className="truncate text-lg font-medium tracking-[-0.02em]">
                {user.username}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">{role}</p>
            </div>
          </div>
          <input
            accept="image/jpeg,image/png,image/webp"
            aria-label="选择头像图片"
            className="hidden"
            onChange={uploadAvatar}
            ref={avatarInput}
            type="file"
          />
          <div className="mt-5 flex flex-wrap gap-2">
            <Button
              disabled={avatarBusy}
              onClick={() => avatarInput.current?.click()}
              size="sm"
              type="button"
              variant="outline"
            >
              {avatarBusy ? (
                <Spinner aria-hidden data-icon="inline-start" />
              ) : (
                <UploadSimpleIcon aria-hidden data-icon="inline-start" />
              )}
              {avatarBusy ? '正在处理头像' : '上传头像'}
            </Button>
            {user.avatar_version ? (
              <Button
                disabled={avatarBusy}
                onClick={() => void deleteAvatar()}
                size="sm"
                type="button"
                variant="ghost"
              >
                <XIcon aria-hidden data-icon="inline-start" />
                移除头像
              </Button>
            ) : null}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            支持 JPEG、PNG、WebP，最大 4 MB；上传后自动裁切为方形。
          </p>
          {avatarError ? (
            <FieldError className="mt-2">{avatarError}</FieldError>
          ) : null}
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
              <FeedbackNotice
                presentation="toast"
                description={notice.text}
                title="资料保存失败"
                tone="error"
              />
            ) : null}
          </FieldGroup>
          <div className="mt-9 flex justify-start">
            <Button disabled={saving || unchanged} type="submit">
              {saving ? (
                <Spinner
                  aria-hidden
                  data-icon="inline-start"
                  role="presentation"
                />
              ) : (
                <FloppyDisk aria-hidden data-icon="inline-start" />
              )}
              {saving ? '正在保存' : '保存资料'}
            </Button>
          </div>
        </div>
      </Form>
    </div>
  );
}
