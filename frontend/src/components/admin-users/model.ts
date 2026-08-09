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
  error: string;
  saving: boolean;
};
