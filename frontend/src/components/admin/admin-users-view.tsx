'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { AdminUsersScreen } from '@/components/admin/admin-users/admin-users-screen';
import {
  type ActiveFilter,
  PAGE_SIZE,
  type RoleFilter,
} from '@/components/admin/admin-users/model';
import {
  AdminSkeleton,
  UnauthenticatedUsers,
} from '@/components/admin/admin-users/user-states';
import { useAuth } from '@/components/auth/auth-provider';
import { displayError, listUsers, updateUserAccess } from '@/services/users';

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
  const [notice, setNotice] = useState('');
  const [editing, setEditing] = useState<API.ManagedUserResponse | null>(null);
  const [editRole, setEditRole] = useState<API.UserRole>('user');
  const [editActive, setEditActive] = useState(true);
  const [editError, setEditError] = useState('');
  const [saving, setSaving] = useState(false);
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
    setEditError('');
  }

  async function saveEditor() {
    if (!editing || editing.id === currentUserId) return;
    setSaving(true);
    setEditError('');
    try {
      await updateUserAccess(editing.id, {
        role: editRole,
        is_active: editActive,
      });
      setEditing(null);
      setNotice(`已更新 ${editing.username} 的账户权限。`);
      await loadUsers();
    } catch (reason) {
      setEditError(displayError(reason));
    } finally {
      setSaving(false);
    }
  }

  if (authLoading) return <AdminSkeleton />;
  if (!user) return <UnauthenticatedUsers />;

  return (
    <AdminUsersScreen
      currentUserId={user.id}
      query={{ draftSearch, role, active }}
      result={{ items, total, page, loading, error }}
      editor={{
        user: editing,
        role: editRole,
        active: editActive,
        error: editError,
        saving,
      }}
      notice={notice}
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
        onEditRole: setEditRole,
        onEditActive: setEditActive,
        onCloseEditor: () => {
          if (!saving) setEditing(null);
        },
        onSaveEditor: () => void saveEditor(),
      }}
    />
  );
}
