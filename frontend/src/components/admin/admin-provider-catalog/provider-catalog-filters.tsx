'use client';

import { MagnifyingGlassIcon } from '@phosphor-icons/react';

import { Field, FieldLabel } from '@/components/ui/field';
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from '@/components/ui/input-group';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export type CatalogVisibility = 'all' | 'visible' | 'hidden';

type ProviderCatalogFiltersProps = {
  query: string;
  visibility: CatalogVisibility;
  onQueryChange: (value: string) => void;
  onVisibilityChange: (value: CatalogVisibility) => void;
};

export function ProviderCatalogFilters({
  query,
  visibility,
  onQueryChange,
  onVisibilityChange,
}: ProviderCatalogFiltersProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_12rem]">
      <Field>
        <FieldLabel htmlFor="provider-catalog-search">搜索平台</FieldLabel>
        <InputGroup className="h-11">
          <InputGroupAddon>
            <MagnifyingGlassIcon aria-hidden />
          </InputGroupAddon>
          <InputGroupInput
            id="provider-catalog-search"
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="搜索名称或目录键"
            type="search"
            value={query}
          />
        </InputGroup>
      </Field>
      <Field>
        <FieldLabel htmlFor="provider-catalog-visibility">公开状态</FieldLabel>
        <Select
          onValueChange={(value) =>
            onVisibilityChange(value as CatalogVisibility)
          }
          value={visibility}
        >
          <SelectTrigger
            className="h-11 w-full"
            id="provider-catalog-visibility"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="visible">公开显示</SelectItem>
            <SelectItem value="hidden">已隐藏</SelectItem>
          </SelectContent>
        </Select>
      </Field>
    </div>
  );
}
