'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { AdminStorageScreen } from '@/components/admin/admin-storage/admin-storage-screen';
import { STORAGE_PAGE_SIZE } from '@/components/admin/admin-storage/model';
import { useAuth } from '@/components/auth/auth-provider';
import {
  cleanupStoredFiles,
  displayError,
  listStoredFiles,
} from '@/services/storage-files';

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
      const result = await cleanupStoredFiles(cleanupDays);
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

  return (
    <AdminStorageScreen
      cleanup={{
        open: cleanupOpen,
        days: cleanupDays,
        cleaning,
        error: cleanupError,
      }}
      error={error}
      items={items}
      loading={loading || authLoading}
      notice={notice}
      onCleanupDaysChange={setCleanupDays}
      onCloseCleanup={() => {
        if (!cleaning) setCleanupOpen(false);
      }}
      onConfirmCleanup={() => void confirmCleanup()}
      onOpenCleanup={() => {
        setCleanupError('');
        setCleanupOpen(true);
      }}
      onPageChange={setPage}
      onRetry={() => void loadFiles()}
      page={page}
      total={total}
    />
  );
}
