import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { accessPolicyLabel, routeCooldownLabel } from '@/lib/provider-access';

export function ProviderAccessSelector({
  provider,
  selected,
  disabled,
  onChange,
}: {
  provider: API.ProviderStatusResponse;
  selected: API.ProviderAccessPolicy | undefined;
  disabled: boolean;
  onChange: (policy: API.ProviderAccessPolicy) => void;
}) {
  if (provider.access_policies.length === 0) return null;
  return (
    <div className="mt-4 space-y-2">
      <Label htmlFor="provider-access-policy">
        {provider.display_name}访问策略
      </Label>
      <Select
        disabled={disabled}
        onValueChange={(value) => onChange(value as API.ProviderAccessPolicy)}
        value={selected}
      >
        <SelectTrigger
          aria-describedby="provider-access-description"
          className="min-h-11 w-full sm:max-w-sm"
          id="provider-access-policy"
        >
          <SelectValue placeholder="使用平台默认策略" />
        </SelectTrigger>
        <SelectContent>
          {provider.access_policies.map((policy) => (
            <SelectItem
              disabled={!policy.configured}
              key={policy.id}
              value={policy.id}
            >
              {accessPolicyLabel[policy.id]}
              {policy.configured ? '' : '（未配置）'}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <p
        className="text-sm text-muted-foreground"
        id="provider-access-description"
      >
        仅处理有权获取的非 DRM 内容；切换策略后需重新解析，不会自动切换会话。
        {provider.evidence_state !== 'fresh'
          ? ' 当前默认线路尚无新鲜验证证据。'
          : null}
      </p>
      {provider.route_retry_at ? (
        <p role="status" className="text-sm text-muted-foreground">
          默认线路{routeCooldownLabel(provider.route_retry_at)}
        </p>
      ) : null}
    </div>
  );
}
