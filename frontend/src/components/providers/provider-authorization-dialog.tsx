'use client';

import { CopyIcon, ShieldCheckIcon } from '@phosphor-icons/react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

const CHROME_AUTH_PROVIDERS = new Set([
  'youtube',
  'douyin',
  'xiaohongshu',
  'x',
  'instagram',
  'facebook',
  'reddit',
  'pinterest',
]);

export function ProviderAuthorizationDialog({
  provider,
}: {
  provider: API.ProviderListResponse['items'][number];
}) {
  const chromeAuthorization = CHROME_AUTH_PROVIDERS.has(provider.key);
  const authorizeCommand = `cd backend && uv run python -m app.workers.runner.provider_cookie_agent authorize --provider ${provider.key}`;
  const installCommand =
    'cd backend && uv run python -m app.workers.runner.provider_cookie_agent install --browser-root "$HOME/Library/Application Support/FrameFetch/provider-browser-sessions"';

  async function copy(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      toast.success('命令已复制');
    } catch {
      toast.error('复制失败，请手动复制命令');
    }
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button size="sm" variant="secondary">
          <ShieldCheckIcon aria-hidden data-icon="inline-start" />
          查看本机授权步骤
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>在当前设备完成平台验证</DialogTitle>
          <DialogDescription>
            不需要常驻机器，也不会把 Cookie 上传到服务端。授权只保存在当前设备的
            平台专用浏览器目录中；平台仍可能要求你在第一方页面完成登录或验证。
          </DialogDescription>
        </DialogHeader>
        {chromeAuthorization ? (
          <div className="space-y-4 text-sm leading-6 text-muted-foreground">
            <p>先运行授权命令，完成登录后保持页面关闭或打开均可：</p>
            <CommandBlock command={authorizeCommand} onCopy={copy} />
            <p>首次配置或重新安装本机按需 Agent：</p>
            <CommandBlock command={installCommand} onCopy={copy} />
            <p>
              Agent 只在解析或下载需要时读取对应平台的最小
              Cookie，并通过一次性加密租约交给受控 Runner；不会生成项目目录下的
              Cookie 文件。
            </p>
          </div>
        ) : (
          <p className="text-sm leading-6 text-muted-foreground">
            该平台使用独立的受控会话来源，不适用 Chrome
            授权命令。请按部署配置启用对应的 Operator Runner 和平台专用
            Agent；系统不会切换到公共代理，也不会绕过验证码或 DRM。
          </p>
        )}
        <DialogFooter>
          <span className="mr-auto text-xs text-muted-foreground">
            当前状态：{accessStateLabel(provider.access_state)}
          </span>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CommandBlock({
  command,
  onCopy,
}: {
  command: string;
  onCopy: (value: string) => Promise<void>;
}) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-muted/60 p-3">
      <code className="min-w-0 flex-1 break-all font-mono text-xs text-foreground">
        {command}
      </code>
      <Button
        aria-label="复制命令"
        onClick={() => void onCopy(command)}
        size="icon-sm"
        variant="ghost"
      >
        <CopyIcon aria-hidden />
      </Button>
    </div>
  );
}

function accessStateLabel(state: API.ProviderAccessState): string {
  const labels: Record<API.ProviderAccessState, string> = {
    public_probe: '公开线路待验证',
    public_ready: '公开线路可用',
    authorization_required: '需要授权或平台验证',
    operator_probe: '受控线路待验证',
    operator_ready: '受控线路可用',
    degraded: '服务降级',
    blocked: '出口受限',
    disabled: '已停用',
    unsupported: '不支持',
  };
  return labels[state];
}
