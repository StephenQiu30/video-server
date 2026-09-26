from app.core.db import as_utc
from app.models import UserRow
from app.services.auth.models import AccountRecord, CurrentUser, UserRole
from app.services.quotas import UserQuota


def account_from_row(row: UserRow) -> AccountRecord:
    return AccountRecord(
        id=row.id,
        username=row.username,
        email=row.email,
        password_hash=row.password_hash,
        role=UserRole(row.role),
        is_active=row.is_active,
        created_at=as_utc(row.created_at),
        updated_at=as_utc(row.updated_at),
        avatar_version=row.avatar_version,
        quota=UserQuota(
            exempt=row.quota_exempt,
            max_active_per_owner=row.quota_max_active_tasks,
            daily_tasks=row.quota_daily_tasks,
            daily_bytes=row.quota_daily_bytes,
            storage_bytes=row.quota_storage_bytes,
            daily_analysis_attempts=row.quota_daily_analysis_attempts,
        ),
    )


def current_user_from_row(row: UserRow) -> CurrentUser:
    return account_from_row(row).public_view()
