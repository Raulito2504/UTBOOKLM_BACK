from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0002_backend_foundation"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


job_status = postgresql.ENUM(
    "pending",
    "processing",
    "completed",
    "failed",
    name="job_status",
    create_type=False,
)
exam_question_type = postgresql.ENUM(
    "multiple_choice",
    "true_false",
    "open",
    name="exam_question_type",
    create_type=False,
)
room_visibility = postgresql.ENUM(
    "public",
    "private",
    name="room_visibility",
    create_type=False,
)
room_role = postgresql.ENUM(
    "owner",
    "editor",
    "reader",
    name="room_role",
    create_type=False,
)
notification_status = postgresql.ENUM(
    "unread",
    "read",
    name="notification_status",
    create_type=False,
)
user_role = postgresql.ENUM(
    "owner",
    "admin",
    "member",
    name="user_role",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    job_status.create(bind, checkfirst=True)
    exam_question_type.create(bind, checkfirst=True)
    room_visibility.create(bind, checkfirst=True)
    room_role.create(bind, checkfirst=True)
    notification_status.create(bind, checkfirst=True)

    op.add_column(
        "documents",
        sa.Column("original_filename", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("mime_type", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "storage_backend",
            sa.String(length=50),
            server_default="local",
            nullable=False,
        ),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("idx_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])

    op.create_table(
        "password_reset_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "idx_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
    )
    op.create_index(
        "idx_password_reset_tokens_expires_at",
        "password_reset_tokens",
        ["expires_at"],
    )

    op.create_table(
        "organization_memberships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", user_role, server_default="member", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_org_memberships_org_user",
        ),
    )
    op.create_index(
        "idx_org_memberships_org_id",
        "organization_memberships",
        ["organization_id"],
    )
    op.create_index(
        "idx_org_memberships_user_id",
        "organization_memberships",
        ["user_id"],
    )

    op.create_table(
        "organization_invitations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, server_default="member", nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "idx_org_invitations_org_id",
        "organization_invitations",
        ["organization_id"],
    )
    op.create_index(
        "idx_org_invitations_email",
        "organization_invitations",
        ["email"],
    )

    op.create_table(
        "ingestion_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", job_status, server_default="pending", nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column(
            "storage_backend",
            sa.String(length=50),
            server_default="local",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ingestion_jobs_document_id", "ingestion_jobs", ["document_id"])
    op.create_index("idx_ingestion_jobs_status", "ingestion_jobs", ["status"])

    op.create_table(
        "rag_queries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_rag_queries_user_id", "rag_queries", ["user_id"])
    op.create_index("idx_rag_queries_org_id", "rag_queries", ["organization_id"])
    op.create_index("idx_rag_queries_document_id", "rag_queries", ["document_id"])

    op.create_table(
        "exams",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_exams_user_id", "exams", ["user_id"])
    op.create_index("idx_exams_document_id", "exams", ["document_id"])

    op.create_table(
        "exam_questions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("exam_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_type", exam_question_type, nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_exam_questions_exam_id", "exam_questions", ["exam_id"])

    op.create_table(
        "exam_attempts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("exam_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("feedback", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_exam_attempts_exam_id", "exam_attempts", ["exam_id"])
    op.create_index("idx_exam_attempts_user_id", "exam_attempts", ["user_id"])

    op.create_table(
        "study_activities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activity_type", sa.String(length=100), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_study_activities_user_id", "study_activities", ["user_id"])
    op.create_index(
        "idx_study_activities_activity_date",
        "study_activities",
        ["activity_date"],
    )

    op.create_table(
        "study_rooms",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "visibility",
            room_visibility,
            server_default="private",
            nullable=False,
        ),
        sa.Column("board_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_study_rooms_org_id", "study_rooms", ["organization_id"])
    op.create_index("idx_study_rooms_owner_id", "study_rooms", ["owner_user_id"])

    op.create_table(
        "room_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", room_role, server_default="reader", nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["room_id"], ["study_rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "user_id", name="uq_room_members_room_user"),
    )
    op.create_index("idx_room_members_room_id", "room_members", ["room_id"])
    op.create_index("idx_room_members_user_id", "room_members", ["user_id"])

    op.create_table(
        "web_sources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", job_status, server_default="pending", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_web_sources_org_id", "web_sources", ["organization_id"])
    op.create_index("idx_web_sources_status", "web_sources", ["status"])

    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            notification_status,
            server_default="unread",
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_notifications_user_id", "notifications", ["user_id"])
    op.create_index("idx_notifications_status", "notifications", ["status"])


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("idx_notifications_status", table_name="notifications")
    op.drop_index("idx_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("idx_web_sources_status", table_name="web_sources")
    op.drop_index("idx_web_sources_org_id", table_name="web_sources")
    op.drop_table("web_sources")
    op.drop_index("idx_room_members_user_id", table_name="room_members")
    op.drop_index("idx_room_members_room_id", table_name="room_members")
    op.drop_table("room_members")
    op.drop_index("idx_study_rooms_owner_id", table_name="study_rooms")
    op.drop_index("idx_study_rooms_org_id", table_name="study_rooms")
    op.drop_table("study_rooms")
    op.drop_index(
        "idx_study_activities_activity_date",
        table_name="study_activities",
    )
    op.drop_index("idx_study_activities_user_id", table_name="study_activities")
    op.drop_table("study_activities")
    op.drop_index("idx_exam_attempts_user_id", table_name="exam_attempts")
    op.drop_index("idx_exam_attempts_exam_id", table_name="exam_attempts")
    op.drop_table("exam_attempts")
    op.drop_index("idx_exam_questions_exam_id", table_name="exam_questions")
    op.drop_table("exam_questions")
    op.drop_index("idx_exams_document_id", table_name="exams")
    op.drop_index("idx_exams_user_id", table_name="exams")
    op.drop_table("exams")
    op.drop_index("idx_rag_queries_document_id", table_name="rag_queries")
    op.drop_index("idx_rag_queries_org_id", table_name="rag_queries")
    op.drop_index("idx_rag_queries_user_id", table_name="rag_queries")
    op.drop_table("rag_queries")
    op.drop_index("idx_ingestion_jobs_status", table_name="ingestion_jobs")
    op.drop_index("idx_ingestion_jobs_document_id", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
    op.drop_index("idx_org_invitations_email", table_name="organization_invitations")
    op.drop_index("idx_org_invitations_org_id", table_name="organization_invitations")
    op.drop_table("organization_invitations")
    op.drop_index(
        "idx_org_memberships_user_id",
        table_name="organization_memberships",
    )
    op.drop_index(
        "idx_org_memberships_org_id",
        table_name="organization_memberships",
    )
    op.drop_table("organization_memberships")
    op.drop_index(
        "idx_password_reset_tokens_expires_at",
        table_name="password_reset_tokens",
    )
    op.drop_index(
        "idx_password_reset_tokens_user_id",
        table_name="password_reset_tokens",
    )
    op.drop_table("password_reset_tokens")
    op.drop_index("idx_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_index("idx_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_column("documents", "storage_backend")
    op.drop_column("documents", "mime_type")
    op.drop_column("documents", "original_filename")

    notification_status.drop(bind, checkfirst=True)
    room_role.drop(bind, checkfirst=True)
    room_visibility.drop(bind, checkfirst=True)
    exam_question_type.drop(bind, checkfirst=True)
    job_status.drop(bind, checkfirst=True)
