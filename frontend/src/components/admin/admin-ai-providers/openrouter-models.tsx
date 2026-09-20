import { useState } from 'react';
import { listOpenRouterModels } from '@/api/admin';
import { FeedbackNotice } from '@/components/layout/feedback-notice';
import { Button } from '@/components/ui/button';
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Spinner } from '@/components/ui/spinner';
import { displayError } from '@/lib/request-error';

export function OpenRouterModels({
  disabled,
  onSelect,
}: {
  disabled: boolean;
  onSelect: (id: string) => void;
}) {
  const [items, setItems] = useState<API.AiModelResponse[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const available = items?.filter(
    (item) =>
      item.input_modalities.includes('text') &&
      item.output_modalities.includes('text') &&
      item.supported_parameters.includes('structured_outputs'),
  );
  const visible = available?.filter((item) =>
    `${item.name} ${item.id}`.toLowerCase().includes(search.toLowerCase()),
  );
  async function load() {
    setLoading(true);
    setError('');
    try {
      setItems((await listOpenRouterModels()).items);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setLoading(false);
    }
  }
  return (
    <Field>
      <div>
        <Button
          disabled={disabled || loading}
          onClick={load}
          type="button"
          variant="outline"
        >
          {loading ? <Spinner aria-hidden data-icon="inline-start" /> : null}
          {loading ? '正在读取模型…' : '读取 OpenRouter 模型'}
        </Button>
      </div>
      {error ? (
        <FeedbackNotice
          description={error}
          title="模型目录读取失败"
          tone="error"
        />
      ) : null}
      {items !== null ? (
        <>
          <FieldLabel htmlFor="openrouter-model-search">搜索模型</FieldLabel>
          <Input
            id="openrouter-model-search"
            value={search}
            disabled={disabled}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="输入模型名称或 ID"
          />
          <FieldLabel htmlFor="openrouter-model-select">
            目录中的模型
          </FieldLabel>
          <Select
            disabled={disabled || !visible?.length}
            onValueChange={onSelect}
          >
            <SelectTrigger
              className="w-full min-w-0"
              id="openrouter-model-select"
            >
              <SelectValue placeholder="选择模型" />
            </SelectTrigger>
            <SelectContent>
              {visible?.map((item) => (
                <SelectItem key={item.id} value={item.id}>
                  {item.id} ·{' '}
                  {item.input_modalities.includes('image')
                    ? '支持图像'
                    : '仅文本'}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FieldDescription aria-live="polite">
            {visible?.length ?? 0}{' '}
            个匹配模型。仅列出声明支持结构化输出的模型；视频请选择支持图像的模型。目录信息不代表实际调用已验证。
          </FieldDescription>
        </>
      ) : null}
    </Field>
  );
}
