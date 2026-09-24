'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { deleteUser, listUsers, updateUserAccess } from '@/api/admin';
import { AdminUsersScreen } from '@/components/admin/admin-users/admin-users-screen';
import {
  type ActiveFilter,
  PAGE_SIZE,
  type RoleFilter,
  type UserQuotaDraft,
} from '@/components/admin/admin-users/model';
import {
  AdminSkeleton,
  UnauthenticatedUsers,
} from '@/components/admin/admin-users/user-states';
import { useAuth } from '@/components/auth/auth-provider';
import { ApiError, displayError } from '@/lib/request-error';

const GIB = 1024 ** 3;
const EMPTY_QUOTA: UserQuotaDraft = {
  exempt: false,
  maxActiveTasks: '',
  dailyTasks: '',
  dailyGiB: '',
  storageGiB: '',
  dailyAnalysisAttempts: '',
};

export function AdminUsersView() {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<API.ManagedUserResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [draftSearch, setDraftSearch] = useState('');
  const [search, setSearch] = useState('');
  const [role, setRole] = useState<RoleFilter>('all');
  const [active, setActive] = useState<ActiveFilter>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState<API.ManagedUserResponse | null>(null);
  const [editRole, setEditRole] = useState<API.UserRole>('user');
  const [editActive, setEditActive] = useState(true);
  const [editQuota, setEditQuota] = useState<UserQuotaDraft>(EMPTY_QUOTA);
  const [editError, setEditError] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] =
    useState<API.ManagedUserResponse | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const requestId = useRef(0);
  const currentUserId = user?.id;

  const loadUsers = useCallback(async () => {
    const current = ++requestId.current;
    setLoading(true);
    setError('');
    try {
      const result = await listUsers({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        role: role === 'all' ? undefined : role,
        is_active: active === 'all' ? undefined : active === 'true',
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
  }, [active, page, role, search]);

  useEffect(() => {
    if (authLoading || !currentUserId) return;
    void loadUsers();
    return () => {
      requestId.current += 1;
    };
  }, [authLoading, currentUserId, loadUsers]);

  function applySearch(value: string) {
    setPage(1);
    setSearch(value);
    if (page === 1 && search === value) void loadUsers();
  }

  function openEditor(target: API.ManagedUserResponse) {
    if (target.id === currentUserId) return;
    setEditing(target);
    setEditRole(target.role);
    setEditActive(target.is_active);
    setEditQuota(quotaDraft(target.quota));
    setEditError('');
  }

  async function saveEditor() {
    if (!editing || editing.id === currentUserId) return;
    setSaving(true);
    setEditError('');
    try {
      const quota = quotaInput(editQuota);
      await updateUserAccess(
        { user_id: encodeURIComponent(editing.id) },
        {
          role: editRole,
          is_active: editActive,
          quota,
        },
      );
      setEditing(null);
      toast.success(`已更新 ${editing.username} 的账户权限。`);
      await loadUsers();
    } catch (reason) {
      setEditError(
        reason instanceof Error && !(reason instanceof ApiError)
          ? reason.message
          : displayError(reason),
      );
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!deleteTarget || deleteTarget.id === currentUserId) return;
    const target = deleteTarget;
    setDeleting(true);
    setDeleteError('');
    try {
      await deleteUser({ user_id: encodeURIComponent(target.id) });
      setDeleteTarget(null);
      toast.success(`已删除账户“${target.username}”。`);
      if (page > 1 && items.length === 1) {
        setPage(page - 1);
      } else {
        await loadUsers();
      }
    } catch (reason) {
      setDeleteError(displayError(reason));
    } finally {
      setDeleting(false);
    }
  }

  if (authLoading) return <AdminSkeleton />;
  if (!user) return <UnauthenticatedUsers />;

  return (
    <AdminUsersScreen
      currentUserId={user.id}
      query={{ draftSearch, role, active }}
      result={{ items, total, page, loading, error }}
      deletion={{
        user: deleteTarget,
        deleting,
        error: deleteError,
      }}
      editor={{
        user: editing,
        role: editRole,
        active: editActive,
        quota: editQuota,
        error: editError,
        saving,
      }}
      actions={{
        onDraftSearch: setDraftSearch,
        onSearch: applySearch,
        onRoleChange: (value) => {
          setRole(value);
          setPage(1);
        },
        onActiveChange: (value) => {
          setActive(value);
          setPage(1);
        },
        onRetry: () => void loadUsers(),
        onPageChange: setPage,
        onEdit: openEditor,
        onDelete: (target) => {
          if (target.id === user.id) return;
          setDeleteError('');
          setDeleteTarget(target);
        },
        onEditRole: setEditRole,
        onEditActive: setEditActive,
        onEditQuota: (field, value) => {
          setEditQuota((current) => ({ ...current, [field]: value }));
          setEditError('');
        },
        onCloseEditor: () => {
          if (!saving) setEditing(null);
        },
        onSaveEditor: () => void saveEditor(),
        onCloseDelete: () => {
          if (!deleting) setDeleteTarget(null);
        },
        onConfirmDelete: () => void confirmDelete(),
      }}
    />
  );
}

function quotaDraft(quota: API.UserQuotaSettings): UserQuotaDraft {
  return {
    exempt: quota.exempt ?? false,
    maxActiveTasks: quota.max_active_per_owner?.toString() ?? '',
    dailyTasks: quota.daily_tasks?.toString() ?? '',
    dailyGiB: bytesToGiB(quota.daily_bytes),
    storageGiB: bytesToGiB(quota.storage_bytes),
    dailyAnalysisAttempts: quota.daily_analysis_attempts?.toString() ?? '',
  };
}

function quotaInput(quota: UserQuotaDraft): API.UserQuotaSettings {
  return {
    exempt: quota.exempt,
    max_active_per_owner: positiveInteger(quota.maxActiveTasks, '同时活跃任务'),
    daily_tasks: positiveInteger(quota.dailyTasks, '24 小时任务数'),
    daily_bytes: positiveGiB(quota.dailyGiB, '24 小时处理量'),
    storage_bytes: positiveGiB(quota.storageGiB, '保留存储'),
    daily_analysis_attempts: positiveInteger(
      quota.dailyAnalysisAttempts,
      '24 小时分析尝试',
    ),
  };
}

function positiveInteger(value: string, label: string): number | null {
  if (!value) return null;
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed <= 0) {
    throw new Error(`${label}必须是正整数。`);
  }
  return parsed;
}

function positiveGiB(value: string, label: string): number | null {
  if (!value) return null;
  const parsed = Number(value);
  const bytes = Math.round(parsed * GIB);
  if (!Number.isFinite(parsed) || parsed <= 0 || !Number.isSafeInteger(bytes)) {
    throw new Error(`${label}必须是大于 0 的有效数值。`);
  }
  return bytes;
}

function bytesToGiB(value: number | null | undefined): string {
  if (value == null) return '';
  return (value / GIB).toString();
}
