import { Key, WarningCircle } from '@phosphor-icons/react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import type { AiProviderEditorState } from './model';

export function AiProviderFields({
  editor,
  onChange,
}: {
  editor: AiProviderEditorState;
  onChange: (values: Partial<AiProviderEditorState>) => void;
}) {
  const creating = editor.mode === 'create';
  return (
    <FieldGroup className="gap-6">
      <div className="grid gap-6 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="ai-provider-key">配置标识</FieldLabel>
          <Input
            autoComplete="off"
            disabled={!creating || editor.saving}
            id="ai-provider-key"
            maxLength={32}
            onChange={(event) => onChange({ key: event.target.value })}
            pattern="[a-z][a-z0-9_-]{0,31}"
            placeholder="openai-main"
            required
            value={editor.key}
          />
          <FieldDescription>创建后不可修改。</FieldDescription>
        </Field>
        <Field>
          <FieldLabel htmlFor="ai-provider-name">显示名称</FieldLabel>
          <Input
            disabled={editor.saving}
            id="ai-provider-name"
            maxLength={64}
            onChange={(event) => onChange({ displayName: event.target.value })}
            placeholder="OpenAI 主线路"
            required
            value={editor.displayName}
          />
        </Field>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="ai-provider-engine">执行引擎</FieldLabel>
          <Select
            disabled={editor.saving}
            onValueChange={(engine: API.AiProviderEngine) =>
              onChange({
                engine,
                model: engine === 'codex' ? 'gpt-5.6-sol' : 'sonnet',
              })
            }
            value={editor.engine}
          >
            <SelectTrigger className="w-full" id="ai-provider-engine">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="codex">Codex CLI · Responses</SelectItem>
              <SelectItem value="claude">Claude CLI · Messages</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        <Field>
          <FieldLabel htmlFor="ai-provider-auth">认证方式</FieldLabel>
          <Select
            disabled={editor.saving}
            onValueChange={(authMode: API.AiProviderAuthMode) =>
              onChange({ authMode, baseUrl: '', apiKey: '' })
            }
            value={editor.authMode}
          >
            <SelectTrigger className="w-full" id="ai-provider-auth">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="host_login">本机账号登录 · 免 Key</SelectItem>
              <SelectItem value="api_key">API Key</SelectItem>
            </SelectContent>
          </Select>
        </Field>
      </div>

      <Field>
        <FieldLabel htmlFor="ai-provider-model">模型</FieldLabel>
        <Input
          disabled={editor.saving}
          id="ai-provider-model"
          maxLength={128}
          onChange={(event) => onChange({ model: event.target.value })}
          placeholder={editor.engine === 'codex' ? 'gpt-5.6-sol' : 'sonnet'}
          required
          value={editor.model}
        />
      </Field>

      {editor.authMode === 'api_key' ? (
        <ApiKeyFields creating={creating} editor={editor} onChange={onChange} />
      ) : (
        <Alert className="border-0 bg-surface">
          <AlertDescription>
            Agent 将读取当前系统用户的{' '}
            {editor.engine === 'codex' ? 'Codex / ChatGPT' : 'Claude'}{' '}
            登录状态；无需在项目中保存 Key。
          </AlertDescription>
        </Alert>
      )}

      {editor.error ? (
        <Alert variant="destructive">
          <WarningCircle aria-hidden />
          <AlertDescription>{editor.error}</AlertDescription>
        </Alert>
      ) : null}
    </FieldGroup>
  );
}

function ApiKeyFields({
  creating,
  editor,
  onChange,
}: {
  creating: boolean;
  editor: AiProviderEditorState;
  onChange: (values: Partial<AiProviderEditorState>) => void;
}) {
  return (
    <>
      <Field>
        <FieldLabel htmlFor="ai-provider-url">API Base URL</FieldLabel>
        <Input
          autoCapitalize="none"
          autoComplete="url"
          disabled={editor.saving}
          id="ai-provider-url"
          maxLength={2048}
          onChange={(event) => onChange({ baseUrl: event.target.value })}
          placeholder={
            editor.engine === 'codex'
              ? 'https://api.openai.com/v1'
              : 'https://api.anthropic.com'
          }
          required
          type="url"
          value={editor.baseUrl}
        />
        <FieldDescription>
          公网地址必须使用 HTTPS；本机 localhost 可使用 HTTP。
        </FieldDescription>
      </Field>
      <Field>
        <FieldLabel htmlFor="ai-provider-secret">API Key</FieldLabel>
        <Input
          autoComplete="new-password"
          disabled={editor.saving}
          id="ai-provider-secret"
          maxLength={4096}
          onChange={(event) => onChange({ apiKey: event.target.value })}
          placeholder={
            creating || !editor.credentialConfigured
              ? '填写服务凭据'
              : '已配置；留空表示不修改'
          }
          required={creating || !editor.credentialConfigured}
          type="password"
          value={editor.apiKey}
        />
        <FieldDescription className="flex items-center gap-1.5">
          <Key aria-hidden className="size-4" />
          保存后仅显示“已配置”，不会再次返回明文。
        </FieldDescription>
      </Field>
    </>
  );
}
