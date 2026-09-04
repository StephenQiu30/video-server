'use client';

import { ArrowRight, FilmStrip } from '@phosphor-icons/react';

import { Button } from '@/components/ui/button';
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemMedia,
  ItemTitle,
} from '@/components/ui/item';
import { Spinner } from '@/components/ui/spinner';
import type { SourceDiscovery, SourceDiscoveryItem } from '@/types/video';

export function SourceDiscoveryWorkspace({
  busyItemRef,
  discovery,
  onSelect,
}: {
  busyItemRef: string | null;
  discovery: SourceDiscovery;
  onSelect: (item: SourceDiscoveryItem) => void;
}) {
  return (
    <section aria-labelledby="source-discovery-title" className="pt-10">
      <div className="flex flex-wrap items-end justify-between gap-3 pb-5">
        <div>
          <h2
            className="text-xl font-medium tracking-[-0.025em]"
            id="source-discovery-title"
          >
            {discovery.title}
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {discovery.items.length > 0
              ? `发现 ${discovery.items.length} 个视频嵌入，请明确选择要处理的项目。`
              : '这篇公开文章中没有发现可识别的视频嵌入。'}
          </p>
        </div>
        <p className="text-xs text-muted-foreground">不会自动选择第一项</p>
      </div>

      {discovery.items.length > 0 ? (
        <ItemGroup asChild className="gap-1" aria-label="文章视频候选项">
          <ul>
            {discovery.items.map((item, index) => {
              const busy = busyItemRef === item.item_ref;
              return (
                <Item
                  asChild
                  className="-mx-3 gap-4 rounded-md border-0 px-3 py-5 hover:bg-muted/50"
                  key={item.item_ref}
                >
                  <li>
                    <ItemMedia className="self-start pt-0.5">
                      <FilmStrip
                        aria-hidden
                        className="text-muted-foreground"
                        size={22}
                      />
                    </ItemMedia>
                    <ItemContent className="min-w-0">
                      <ItemTitle asChild className="truncate">
                        <h3>{item.title || `文章视频 ${index + 1}`}</h3>
                      </ItemTitle>
                      <ItemDescription className="mt-0 text-xs leading-5">
                        {itemKindLabel(item.kind)} · {decisionLabel(item)}
                      </ItemDescription>
                    </ItemContent>
                    <ItemActions className="w-full sm:w-auto">
                      <Button
                        className="h-11 w-full sm:w-auto"
                        disabled={busyItemRef !== null}
                        onClick={() => onSelect(item)}
                        variant="secondary"
                      >
                        {busy ? (
                          <Spinner aria-hidden />
                        ) : (
                          <ArrowRight aria-hidden />
                        )}
                        {busy ? '处理中…' : '选择并查看'}
                      </Button>
                    </ItemActions>
                  </li>
                </Item>
              );
            })}
          </ul>
        </ItemGroup>
      ) : (
        <p className="py-8 text-sm text-muted-foreground" role="status">
          请检查文章是否仍公开，或改用自有明文 MP4 导入。
        </p>
      )}
    </section>
  );
}

function itemKindLabel(kind: SourceDiscoveryItem['kind']) {
  if (kind === 'official_account_native') return '公众号原生视频';
  if (kind === 'tencent_video') return '腾讯视频';
  if (kind === 'wechat_channels') return '微信视频号';
  return '未知嵌入';
}

function decisionLabel(item: SourceDiscoveryItem) {
  if (item.status === 'identity_unverified') return '身份无法可靠绑定';
  if (item.decision_hint === 'export_required') return '需要导入自有文件';
  if (item.decision_hint === 'candidate') return '已发现，下载能力待验收';
  return '仅查看支持状态';
}
