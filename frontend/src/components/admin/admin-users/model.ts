export const PAGE_SIZE = 20;

export type RoleFilter = 'all' | API.UserRole;
export type ActiveFilter = 'all' | 'true' | 'false';

export type UserQueryState = {
  draftSearch: string;
  role: RoleFilter;
  active: ActiveFilter;
};

export type UserResultState = {
  items: API.ManagedUserResponse[];
  total: number;
  page: number;
  loading: boolean;
  error: string;
};

export type UserEditorState = {
  user: API.ManagedUserResponse | null;
  role: API.UserRole;
  active: boolean;
  quota: UserQuotaDraft;
  error: string;
  saving: boolean;
};

export type UserDeletionState = {
  user: API.ManagedUserResponse | null;
  deleting: boolean;
  error: string;
};

export type UserQuotaDraft = {
  exempt: boolean;
  maxActiveTasks: string;
  dailyTasks: string;
  dailyGiB: string;
  storageGiB: string;
  dailyAnalysisAttempts: string;
};
