'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AiProviderDelete } from '@/components/admin-ai-providers/ai-provider-delete';
import { AiProviderEditor } from '@/components/admin-ai-providers/ai-provider-editor';
import { AiProviderScreen } from '@/components/admin-ai-providers/ai-provider-screen';
import {
  type AiProviderEditorState,
  EMPTY_AI_PROVIDER_EDITOR,
} from '@/components/admin-ai-providers/model';
import {
  activateAiProviderProfile,
  createAiProviderProfile,
  deleteAiProviderProfile,
  displayError,
  listAiProviderProfiles,
  updateAiProviderProfile,
} from '@/services/ai-providers';

export function AdminAiProvidersView() {
  const [items, setItems] = useState<API.AiProviderProfileResponse[]>([]);
  const [agentAvailable, setAgentAvailable] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editor, setEditor] = useState<AiProviderEditorState>(
    EMPTY_AI_PROVIDER_EDITOR,
  );
  const [deleteTarget, setDeleteTarget] =
    useState<API.AiProviderProfileResponse | null>(null);
  const [deleting, setDeleting] = useState(false);
  const requestId = useRef(0);

  const load = useCallback(async () => {
    const current = ++requestId.current;
    setLoading(true);
    setError('');
    try {
      const result = await listAiProviderProfiles();
      if (current === requestId.current) {
        setItems(result.items);
        setAgentAvailable(result.agent_available);
      }
    } catch (reason) {
      if (current === requestId.current) setError(displayError(reason));
    } finally {
      if (current === requestId.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    return () => {
      requestId.current += 1;
    };
  }, [load]);

  function openCreate() {
    setNotice('');
    setEditor({ ...EMPTY_AI_PROVIDER_EDITOR, mode: 'create' });
  }

  function openEdit(item: API.AiProviderProfileResponse) {
    setNotice('');
    setEditor({
      mode: 'edit',
      key: item.key,
      displayName: item.display_name,
      engine: item.engine,
      authMode: item.auth_mode,
      baseUrl: item.base_url || '',
      model: item.model,
      apiKey: '',
      credentialConfigured: item.credential_configured,
      error: '',
      saving: false,
    });
  }

  async function saveEditor() {
    if (!editor.mode) return;
    const key = editor.key.trim();
    const displayName = editor.displayName.trim();
    const model = editor.model.trim();
    const baseUrl = editor.baseUrl.trim();
    const apiKey = editor.apiKey.trim();
    if (
      !key ||
      !displayName ||
      !model ||
      (editor.authMode === 'api_key' &&
        (!baseUrl || (!apiKey && !editor.credentialConfigured)))
    ) {
      setEditor((current) => ({
        ...current,
        error: '请补全名称、模型、服务地址与所需凭据。',
      }));
      return;
    }
    setEditor((current) => ({ ...current, saving: true, error: '' }));
    try {
      if (editor.mode === 'create') {
        await createAiProviderProfile({
          key,
          display_name: displayName,
          engine: editor.engine,
          auth_mode: editor.authMode,
          base_url: editor.authMode === 'api_key' ? baseUrl : null,
          model,
          api_key: apiKey || null,
        });
        setNotice(`已新增 AI Provider“${displayName}”。`);
      } else {
        await updateAiProviderProfile(key, {
          display_name: displayName,
          engine: editor.engine,
          auth_mode: editor.authMode,
          base_url: editor.authMode === 'api_key' ? baseUrl : null,
          model,
          ...(apiKey ? { api_key: apiKey } : {}),
        });
        setNotice(`已更新 AI Provider“${displayName}”。`);
      }
      setEditor(EMPTY_AI_PROVIDER_EDITOR);
      await load();
    } catch (reason) {
      setEditor((current) => ({
        ...current,
        saving: false,
        error: displayError(reason),
      }));
    }
  }

  async function activate(item: API.AiProviderProfileResponse) {
    setError('');
    setNotice('');
    try {
      await activateAiProviderProfile(item.key);
      setNotice(`“${item.display_name}”已成为当前分析线路。`);
      await load();
    } catch (reason) {
      setError(displayError(reason));
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteAiProviderProfile(deleteTarget.key);
      setNotice(`已删除 AI Provider“${deleteTarget.display_name}”。`);
      setDeleteTarget(null);
      await load();
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <AiProviderScreen
        agentAvailable={agentAvailable}
        error={error}
        items={items}
        loading={loading}
        notice={notice}
        onActivate={(item) => void activate(item)}
        onCreate={openCreate}
        onDelete={setDeleteTarget}
        onEdit={openEdit}
        onRetry={() => void load()}
      />
      <AiProviderEditor
        editor={editor}
        onChange={(values) =>
          setEditor((current) => ({ ...current, ...values, error: '' }))
        }
        onClose={() => setEditor(EMPTY_AI_PROVIDER_EDITOR)}
        onSave={() => void saveEditor()}
      />
      <AiProviderDelete
        deleting={deleting}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => void confirmDelete()}
        target={deleteTarget}
      />
    </>
  );
}
