'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import {
  cleanupStoredFiles,
  deleteStoredFile,
  listStoredFiles,
} from '@/api/admin';
import { AdminStorageScreen } from '@/components/admin/admin-storage/admin-storage-screen';
import { useAuth } from '@/components/auth/auth-provider';
import { DEFAULT_PAGE_SIZE } from '@/components/layout/page-pagination';
import { displayError } from '@/lib/request-error';

export function AdminStorageView() {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<API.StoredFileResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
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
        page_size: pageSize,
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
  }, [page, pageSize]);

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
      const message = `已清理 ${result.removed_resources} 项资源、${result.removed_objects} 个对象；${result.failed_resources} 项清理失败。`;
      if (result.failed_resources > 0) toast.warning(message);
      else toast.success(message);
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
      toast.success(`已删除文件“${target.name}”。`);
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
      bulk={{
        scope: JSON.stringify([user?.id, page, pageSize]),
        disabled:
          loading ||
          authLoading ||
          cleaning ||
          deleting ||
          cleanupOpen ||
          Boolean(deleteTarget),
        description: '所选文件及关联存储对象将永久删除。',
        remove: (id) => {
          const item = items.find(
            (item) => `${item.category}:${item.id}` === id,
          );
          if (!item)
            return Promise.reject(new Error('文件已变化，请刷新列表。'));
          return deleteStoredFile({
            category: item.category,
            file_id: item.id,
          });
        },
        onComplete: async (done) => {
          if (page > 1 && done.length === items.length) setPage(page - 1);
          else await loadFiles();
        },
      }}
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
      pageSize={pageSize}
      onPageSizeChange={(size) => {
        setPageSize(size);
        setPage(1);
      }}
      total={total}
    />
  );
}
