"""Add notebook and document scopes to study practice artifacts.

Revision ID: 0004_add_study_practice_scope
Revises: 0003_update_user_roles
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0004_add_study_practice_scope"
down_revision: str | None = "0003_update_user_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "flashcard_decks",
        sa.Column(
            "document_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            server_default=sa.text("'{}'::uuid[]"),
            nullable=False,
        ),
    )
    op.add_column(
        "flashcard_decks",
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_flashcard_decks_notebook_id_chat_sessions",
        "flashcard_decks",
        "chat_sessions",
        ["notebook_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_flashcard_decks_notebook_id",
        "flashcard_decks",
        ["notebook_id"],
    )
    op.execute(
        """
        UPDATE flashcard_decks
        SET document_ids = ARRAY[document_id]::uuid[]
        WHERE document_id IS NOT NULL AND document_ids = '{}'::uuid[]
        """,
    )

    op.add_column(
        "exams",
        sa.Column(
            "document_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            server_default=sa.text("'{}'::uuid[]"),
            nullable=False,
        ),
    )
    op.add_column(
        "exams",
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_exams_notebook_id_chat_sessions",
        "exams",
        "chat_sessions",
        ["notebook_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_exams_notebook_id", "exams", ["notebook_id"])
    op.execute(
        """
        UPDATE exams
        SET document_ids = ARRAY[document_id]::uuid[]
        WHERE document_id IS NOT NULL AND document_ids = '{}'::uuid[]
        """,
    )


def downgrade() -> None:
    op.drop_index("idx_exams_notebook_id", table_name="exams")
    op.drop_constraint(
        "fk_exams_notebook_id_chat_sessions",
        "exams",
        type_="foreignkey",
    )
    op.drop_column("exams", "notebook_id")
    op.drop_column("exams", "document_ids")

    op.drop_index("idx_flashcard_decks_notebook_id", table_name="flashcard_decks")
    op.drop_constraint(
        "fk_flashcard_decks_notebook_id_chat_sessions",
        "flashcard_decks",
        type_="foreignkey",
    )
    op.drop_column("flashcard_decks", "notebook_id")
    op.drop_column("flashcard_decks", "document_ids")
