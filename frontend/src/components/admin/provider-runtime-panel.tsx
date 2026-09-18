'use client';

import { useState } from 'react';
import { getAdminProviderRuntime } from '@/api/admin';
import {
  accessPolicyLabel,
  routeCooldownLabel,
} from '@/components/providers/provider-access';
import { Button } from '@/components/ui/button';
import { displayError } from '@/lib/request-error';

const sourceLabels: Record<
  API.ProviderRuntimeResponse['source_state'],
  string
> = {
  not_required: '不需要持久来源',
  revision_observed: '已观测来源修订，授权有效性仍需验证',
  not_observed: '尚未观测来源修订',
  unknown: '来源状态未知',
};

export function ProviderRuntimePanel() {
  const [data, setData] = useState<API.ProviderRuntimeListResponse>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  async function load() {
    if (loading) return;
    setLoading(true);
    setError('');
    setData(undefined);
    try {
      setData(await getAdminProviderRuntime());
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setLoading(false);
    }
  }
  return (
    <section
      aria-labelledby="provider-runtime-title"
      className="mt-10 space-y-4"
    >
      <h2 className="text-base font-medium" id="provider-runtime-title">
        运行诊断
      </h2>
      <p className="text-sm text-muted-foreground">
        仅展示已开放平台的默认线路；快照最多缓存 30
        秒。配置和上下文可达不代表真实下载通过。
      </p>
      <Button
        disabled={loading}
        onClick={() => void load()}
        variant="secondary"
      >
        {loading ? '读取中…' : '读取运行诊断'}
      </Button>
      {error ? <p role="alert">{error}</p> : null}
      {data ? (
        <ul aria-label="平台运行诊断" className="space-y-5">
          {data.items.map((item) => (
            <li className="space-y-1 text-sm" key={item.provider_key}>
              <h3 className="font-medium">
                {item.provider_key}
                {item.access_policy_id
                  ? ` · ${accessPolicyLabel[item.access_policy_id]}`
                  : ''}
              </h3>
              <p>
                {item.route_configured ? '线路已配置' : '线路未配置'} ·{' '}
                {item.context_available
                  ? '上下文可达'
                  : '上下文不可达或尚未确认'}
              </p>
              <p>{sourceLabels[item.source_state]}</p>
              {item.route_retry_at ? (
                <p>{routeCooldownLabel(item.route_retry_at)}</p>
              ) : null}
              <p className="break-words text-muted-foreground">
                引擎：{item.engine_commit ?? '未知'} · 证据：
                {item.evidence_state === 'fresh'
                  ? '近期记录'
                  : item.evidence_state === 'stale'
                    ? '记录已过期'
                    : '无当前记录'}
              </p>
              {item.user_action ? (
                <p className="text-muted-foreground">{item.user_action}</p>
              ) : null}
            </li>
          ))}
          {data.items.length === 0 ? <li>暂无已开放平台。</li> : null}
        </ul>
      ) : null}
    </section>
  );
}
