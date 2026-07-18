"""Prevent rights supersession from rewriting durable attestations.

Revision ID: 0003_rights_attestation_history
Revises: 0002_resolution_aggregate
"""

from __future__ import annotations

from migrations.revision_ddl.r0003_rights_attestation_guard import (
    install_rights_catalog_guard,
)

revision = "0003_rights_attestation_history"
down_revision = "0002_resolution_aggregate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    install_rights_catalog_guard(protect_attestations=True)


def downgrade() -> None:
    install_rights_catalog_guard(protect_attestations=False)
