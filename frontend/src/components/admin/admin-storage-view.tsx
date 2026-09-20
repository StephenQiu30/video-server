'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  cleanupStoredFiles,
  deleteStoredFile,
  listStoredFiles,
} from '@/api/admin';
import { AdminStorageScreen } from '@/components/admin/admin-storage/admin-storage-screen';
import { STORAGE_PAGE_SIZE } from '@/components/admin/admin-storage/model';
import { useAuth } from '@/components/auth/auth-provider';
import { displayError } from '@/lib/request-error';

export function AdminStorageView() {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<API.StoredFileResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [cleanupOpen, setCleanupOpen] = useState(false);
  const [cleanupDays, setCleanupDays] = useState(30);
  const [cleaning, setCleaning] = useState(false);
  const [cleanupError, setCleanupError] = useState('');
  const [deleteTarget, setDeleteTarget] =
    useState<API.StoredFileResponse | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const requestId = useRef(0);

  const loadFiles = useCallback(async () => {
    const current = ++requestId.current;
    setLoading(true);
    setError('');
    try {
      const result = await listStoredFiles({
        page,
        page_size: STORAGE_PAGE_SIZE,
      });
      if (current === requestId.current) {
        setItems(result.items);
        setTotal(result.total);
      }
    } catch (reason) {
      if (current === requestId.current) setError(displayError(reason));
    } finally {
      if (current === requestId.current) setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    if (authLoading || !user) return;
    void loadFiles();
    return () => {
      requestId.current += 1;
    };
  }, [authLoading, user, loadFiles]);

  async function confirmCleanup() {
    setCleaning(true);
    setCleanupError('');
    try {
      const result = await cleanupStoredFiles({ older_than_days: cleanupDays });
      setCleanupOpen(false);
      setNotice(
        `已清理 ${result.removed_resources} 项资源、${result.removed_objects} 个对象；${result.failed_resources} 项清理失败。`,
      );
      if (page === 1) await loadFiles();
      else setPage(1);
    } catch (reason) {
      setCleanupError(displayError(reason));
    } finally {
      setCleaning(false);
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    const target = deleteTarget;
    setDeleting(true);
    setDeleteError('');
    try {
      await deleteStoredFile({ category: target.category, file_id: target.id });
      setDeleteTarget(null);
      setNotice(`已删除文件“${target.name}”。`);
      if (page > 1 && items.length === 1) {
        setPage(page - 1);
      } else {
        await loadFiles();
      }
    } catch (reason) {
      setDeleteError(displayError(reason));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <AdminStorageScreen
      cleanup={{
        open: cleanupOpen,
        days: cleanupDays,
        cleaning,
        error: cleanupError,
      }}
      deletion={{ item: deleteTarget, deleting, error: deleteError }}
      error={error}
      items={items}
      loading={loading || authLoading}
      notice={notice}
      onCleanupDaysChange={setCleanupDays}
      onCloseCleanup={() => {
        if (!cleaning) setCleanupOpen(false);
      }}
      onConfirmCleanup={() => void confirmCleanup()}
      onCloseDelete={() => {
        if (!deleting) setDeleteTarget(null);
      }}
      onConfirmDelete={() => void confirmDelete()}
      onOpenCleanup={() => {
        setCleanupError('');
        setCleanupOpen(true);
      }}
      onOpenDelete={(item) => {
        setDeleteError('');
        setDeleteTarget(item);
      }}
      onPageChange={setPage}
      onRetry={() => void loadFiles()}
      page={page}
      total={total}
    />
  );
}
