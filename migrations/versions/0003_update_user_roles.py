"""Update user roles for product roles.

Revision ID: 0003_update_user_roles
Revises: 0002_backend_foundation
Create Date: 2026-07-06
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0003_update_user_roles"
down_revision: str | None = "0002_backend_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ROLE_COLUMNS = (
    ("users", "role"),
    ("organization_memberships", "role"),
    ("organization_invitations", "role"),
)


def _drop_role_defaults() -> None:
    for table_name, column_name in ROLE_COLUMNS:
        op.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} DROP DEFAULT")


def _set_role_defaults(default: str) -> None:
    for table_name, column_name in ROLE_COLUMNS:
        op.execute(
            f"ALTER TABLE {table_name} ALTER COLUMN {column_name} "
            f"SET DEFAULT '{default}'",
        )


def upgrade() -> None:
    _drop_role_defaults()

    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'teacher', 'student')")

    for table_name, column_name in ROLE_COLUMNS:
        op.execute(
            f"""
            ALTER TABLE {table_name}
            ALTER COLUMN {column_name}
            TYPE user_role
            USING (
                CASE {column_name}::text
                    WHEN 'owner' THEN 'admin'
                    WHEN 'admin' THEN 'admin'
                    ELSE 'student'
                END
            )::user_role
            """,
        )

    _set_role_defaults("student")
    op.execute("DROP TYPE user_role_old")


def downgrade() -> None:
    _drop_role_defaults()

    op.execute("ALTER TYPE user_role RENAME TO user_role_new")
    op.execute("CREATE TYPE user_role AS ENUM ('owner', 'admin', 'member')")

    for table_name, column_name in ROLE_COLUMNS:
        op.execute(
            f"""
            ALTER TABLE {table_name}
            ALTER COLUMN {column_name}
            TYPE user_role
            USING (
                CASE {column_name}::text
                    WHEN 'admin' THEN 'admin'
                    ELSE 'member'
                END
            )::user_role
            """,
        )

    _set_role_defaults("member")
    op.execute("DROP TYPE user_role_new")
