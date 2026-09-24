'use client';

import { useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export function useHistoryRecordFilters() {
  const search = useSearchParams();
  const cursors = search.getAll('cursor');
  const cursor = cursors.at(-1)?.split('|');
  const category = search.get('category') ?? 'all';
  const subkind = search.get('subkind') ?? 'all';
  const recordTypes: API.HistoryRecordKind[] =
    category === 'parse'
      ? ['parse']
      : category === 'video'
        ? ['video_analysis']
        : category === 'screenplay'
          ? subkind === 'basic'
            ? ['document_parse']
            : subkind === 'all'
              ? ['document_parse', 'screenplay_analysis']
              : ['screenplay_analysis']
          : [];
  const filters: API.listHistoryRecordsParams = {
    record_type: recordTypes.length ? recordTypes : undefined,
    status_group: (search.get('status') || undefined) as
      | API.HistoryStatusGroup
      | undefined,
    q: search.get('q') || undefined,
    skill_id: search.get('skill') || undefined,
    result_contract:
      category === 'screenplay' && subkind === 'rewrite'
        ? 'screenplay-rewrite'
        : category === 'screenplay' && subkind === 'analysis'
          ? 'screenplay-analysis'
          : undefined,
    created_from: dateBoundary(search.get('from'), false),
    created_to: dateBoundary(search.get('to'), true),
    document_id: search.get('document_id') || undefined,
    download_id: search.get('download_id') || undefined,
    before_created_at: cursor?.[0],
    before_record_type: cursor?.[1] as API.HistoryRecordKind | undefined,
    before_id: cursor?.[2],
    limit: 20,
  };
  function navigate(params: URLSearchParams) {
    window.history.pushState(
      null,
      '',
      `${window.location.pathname}${params.size ? `?${params}` : ''}`,
    );
  }
  function update(values: Record<string, string>) {
    const params = new URLSearchParams(search.toString());
    params.delete('cursor');
    for (const [key, value] of Object.entries(values)) {
      if (value && value !== 'all') params.set(key, value);
      else params.delete(key);
    }
    navigate(params);
  }
  return {
    filters,
    category,
    subkind,
    page: cursors.length + 1,
    search,
    update,
    hasFilters: Boolean(search.size - cursors.length),
    reset: () => navigate(new URLSearchParams()),
    first: () => {
      const params = new URLSearchParams(search.toString());
      params.delete('cursor');
      navigate(params);
    },
    goToPage: (page: number) => {
      if (page < 1 || page >= cursors.length + 1) return;
      const params = new URLSearchParams(search.toString());
      params.delete('cursor');
      for (const c of cursors.slice(0, page - 1)) params.append('cursor', c);
      navigate(params);
    },
    next: (value: API.HistoryRecordCursorResponse) => {
      const params = new URLSearchParams(search.toString());
      params.append(
        'cursor',
        `${value.created_at}|${value.record_type}|${value.id}`,
      );
      navigate(params);
    },
  };
}

function dateBoundary(value: string | null, end: boolean) {
  if (!value) return undefined;
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return undefined;
  if (end) date.setDate(date.getDate() + 1);
  return date.toISOString();
}

export function HistoryRecordFilters({
  state,
  skills,
}: {
  state: ReturnType<typeof useHistoryRecordFilters>;
  skills: API.AnalysisSkillResponse[];
}) {
  const { search, update, category } = state;
  const categories = [
    ['all', '全部'],
    ['parse', '链接解析'],
    ['video', '视频 AI'],
    ['screenplay', '剧本解析'],
  ];
  return (
    <div className="mt-8 space-y-4">
      <fieldset className="flex flex-wrap gap-2" aria-label="解析类型">
        {categories.map(([value, label]) => (
          <Button
            key={value}
            variant={category === value ? 'secondary' : 'ghost'}
            aria-pressed={category === value}
            onClick={() =>
              update({
                category: value,
                subkind: '',
                skill: '',
                document_id: '',
                download_id: '',
              })
            }
          >
            {label}
          </Button>
        ))}
      </fieldset>
      <form
        className="flex flex-wrap items-end gap-3"
        key={search.toString()}
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          update({
            q: String(data.get('q') ?? ''),
            from: String(data.get('from') ?? ''),
            to: String(data.get('to') ?? ''),
          });
        }}
      >
        <label
          htmlFor="history-title"
          className="grid flex-1 gap-2 text-sm min-w-48"
        >
          内容标题
          <Input
            id="history-title"
            name="q"
            defaultValue={search.get('q') ?? ''}
            maxLength={100}
            placeholder="搜索内容标题"
          />
        </label>
        <label htmlFor="history-from" className="grid gap-2 text-sm">
          开始日期
          <Input
            type="date"
            id="history-from"
            name="from"
            defaultValue={search.get('from') ?? ''}
          />
        </label>
        <label htmlFor="history-to" className="grid gap-2 text-sm">
          结束日期
          <Input
            type="date"
            id="history-to"
            name="to"
            defaultValue={search.get('to') ?? ''}
            min={search.get('from') ?? undefined}
          />
        </label>
        <Button type="submit" variant="outline">
          筛选
        </Button>
        {state.hasFilters ? (
          <Button type="button" variant="ghost" onClick={state.reset}>
            清除筛选
          </Button>
        ) : null}
      </form>
      <div className="flex flex-wrap gap-3">
        <FilterSelect
          label="任务状态"
          value={search.get('status') ?? 'all'}
          onChange={(value) => update({ status: value })}
          options={[
            ['all', '全部状态'],
            ['processing', '处理中'],
            ['action_required', '等待操作'],
            ['completed', '已完成'],
            ['failed', '失败'],
            ['cancelled', '已取消'],
            ['expired', '已过期'],
          ]}
        />
        {category === 'screenplay' ? (
          <FilterSelect
            label="剧本处理类型"
            value={state.subkind}
            onChange={(value) => update({ subkind: value, skill: '' })}
            options={[
              ['all', '全部剧本处理'],
              ['basic', '基础解析'],
              ['analysis', 'AI 分析'],
              ['rewrite', 'AI 改写'],
            ]}
          />
        ) : null}
        {category !== 'parse' &&
        !(category === 'screenplay' && state.subkind === 'basic') ? (
          <FilterSelect
            label="分析 Skill"
            value={search.get('skill') ?? 'all'}
            onChange={(value) => update({ skill: value })}
            options={[
              ['all', '全部 Skill'],
              ...skills.map((skill) => [skill.id, skill.display_name]),
            ]}
          />
        ) : null}
        {search.get('document_id') || search.get('download_id') ? (
          <span className="self-center text-sm text-muted-foreground">
            仅查看此素材的记录
          </span>
        ) : null}
      </div>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[][];
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger aria-label={label}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map(([id, text]) => (
          <SelectItem value={id} key={id}>
            {text}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
