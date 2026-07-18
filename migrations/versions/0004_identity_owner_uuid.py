"""Create PostgreSQL identities and bind aggregate owners to UUID users.

Revision ID: 0004_identity_owner_uuid
Revises: 0003_rights_attestation_history
"""

from __future__ import annotations

from migrations.revision_ddl.r0004_identity_tables import (
    create_identity_tables,
    drop_identity_tables,
)
from migrations.revision_ddl.r0004_owner_constraints import (
    create_text_owner_dependencies,
    create_uuid_owner_dependencies,
    drop_text_owner_dependencies,
    drop_uuid_owner_dependencies,
)
from migrations.revision_ddl.r0004_owner_types import (
    alter_owner_columns_to_text,
    alter_owner_columns_to_uuid,
)
from migrations.revision_ddl.r0004_preflight import (
    require_empty_identity_for_downgrade,
    require_empty_legacy_aggregate_for_upgrade,
)

revision = "0004_identity_owner_uuid"
down_revision = "0003_rights_attestation_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    require_empty_legacy_aggregate_for_upgrade()
    create_identity_tables()
    drop_text_owner_dependencies()
    alter_owner_columns_to_uuid()
    create_uuid_owner_dependencies()


def downgrade() -> None:
    require_empty_identity_for_downgrade()
    drop_uuid_owner_dependencies()
    alter_owner_columns_to_text()
    create_text_owner_dependencies()
    drop_identity_tables()
