'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  type CatalogDeleteState,
  type CatalogEditorState,
  EMPTY_EDITOR,
} from '@/components/admin-provider-catalog/model';
import { ProviderCatalogDelete } from '@/components/admin-provider-catalog/provider-catalog-delete';
import { ProviderCatalogEditor } from '@/components/admin-provider-catalog/provider-catalog-editor';
import { ProviderCatalogScreen } from '@/components/admin-provider-catalog/provider-catalog-screen';
import {
  createProviderCatalogEntry,
  deleteProviderCatalogEntry,
  displayError,
  listProviderCatalogEntries,
  updateProviderCatalogEntry,
} from '@/services/provider-catalog';

const EMPTY_DELETE: CatalogDeleteState = {
  target: null,
  error: '',
  deleting: false,
};

export function AdminProviderCatalogView() {
  const [items, setItems] = useState<API.ProviderCatalogEntryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editor, setEditor] = useState<CatalogEditorState>(EMPTY_EDITOR);
  const [deleting, setDeleting] = useState<CatalogDeleteState>(EMPTY_DELETE);
  const requestId = useRef(0);

  const loadCatalog = useCallback(async () => {
    const current = ++requestId.current;
    setLoading(true);
    setError('');
    try {
      const result = await listProviderCatalogEntries();
      if (current === requestId.current) setItems(result.items);
    } catch (reason) {
      if (current === requestId.current) setError(displayError(reason));
    } finally {
      if (current === requestId.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCatalog();
    return () => {
      requestId.current += 1;
    };
  }, [loadCatalog]);

  function openCreate() {
    setNotice('');
    setEditor({ ...EMPTY_EDITOR, mode: 'create' });
  }

  function openEdit(item: API.ProviderCatalogEntryResponse) {
    setNotice('');
    setEditor({
      mode: 'edit',
      key: item.key,
      displayName: item.display_name,
      sortOrder: String(item.sort_order),
      visible: item.is_visible,
      systemRegistered: item.system_registered,
      error: '',
      saving: false,
    });
  }

  async function saveEditor() {
    if (!editor.mode) return;
    const key = editor.key.trim();
    const displayName = editor.displayName.trim();
    const sortOrder = Number(editor.sortOrder);
    if (!displayName || !Number.isInteger(sortOrder)) {
      setEditor((current) => ({
        ...current,
        error: '请填写有效的显示名称和整数排序值。',
      }));
      return;
    }
    setEditor((current) => ({ ...current, saving: true, error: '' }));
    try {
      if (editor.mode === 'create') {
        await createProviderCatalogEntry({
          key,
          display_name: displayName,
          sort_order: sortOrder,
          is_visible: editor.visible,
        });
        setNotice(`已新增平台“${displayName}”。`);
      } else {
        await updateProviderCatalogEntry(key, {
          display_name: displayName,
          sort_order: sortOrder,
          is_visible: editor.visible,
        });
        setNotice(`已更新平台“${displayName}”。`);
      }
      setEditor(EMPTY_EDITOR);
      await loadCatalog();
    } catch (reason) {
      setEditor((current) => ({
        ...current,
        saving: false,
        error: displayError(reason),
      }));
    }
  }

  async function confirmDelete() {
    if (!deleting.target) return;
    const target = deleting.target;
    setDeleting((current) => ({ ...current, deleting: true, error: '' }));
    try {
      await deleteProviderCatalogEntry(target.key);
      setDeleting(EMPTY_DELETE);
      setNotice(`已删除平台“${target.display_name}”。`);
      await loadCatalog();
    } catch (reason) {
      setDeleting((current) => ({
        ...current,
        deleting: false,
        error: displayError(reason),
      }));
    }
  }

  return (
    <>
      <ProviderCatalogScreen
        notice={notice}
        onCreate={openCreate}
        onDelete={(target) => setDeleting({ ...EMPTY_DELETE, target })}
        onEdit={openEdit}
        onRetry={() => void loadCatalog()}
        result={{ items, loading, error }}
      />
      <ProviderCatalogEditor
        editor={editor}
        onChange={(values) =>
          setEditor((current) => ({ ...current, ...values, error: '' }))
        }
        onClose={() => setEditor(EMPTY_EDITOR)}
        onSave={() => void saveEditor()}
      />
      <ProviderCatalogDelete
        onClose={() => setDeleting(EMPTY_DELETE)}
        onConfirm={() => void confirmDelete()}
        state={deleting}
      />
    </>
  );
}
