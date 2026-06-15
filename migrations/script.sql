-- Extensión para generar UUIDs de forma segura
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================================
-- ENUMS
-- =========================================

CREATE TYPE plan_type AS ENUM ('free', 'pro');
CREATE TYPE user_role AS ENUM ('owner', 'admin', 'member');
CREATE TYPE document_status AS ENUM ('processing', 'ready', 'failed');
CREATE TYPE message_role AS ENUM ('user', 'assistant');
CREATE TYPE flashcard_difficulty AS ENUM ('easy', 'medium', 'hard');

-- =========================================
-- ORGANIZATIONS
-- =========================================

CREATE TABLE organizations (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        varchar(255) NOT NULL,
    slug        varchar(255) NOT NULL UNIQUE,
    plan        plan_type NOT NULL DEFAULT 'free',
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

-- =========================================
-- USERS
-- =========================================

CREATE TABLE users (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email           varchar(255) NOT NULL UNIQUE,
    password_hash   varchar(255) NOT NULL,
    name            varchar(255) NOT NULL,
    role            user_role NOT NULL DEFAULT 'member',
    is_active       boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_org_id ON users(organization_id);

-- =========================================
-- DOCUMENTS
-- =========================================

CREATE TABLE documents (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    uploaded_by_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title              varchar(255) NOT NULL,
    file_path          varchar(1024) NOT NULL,
    file_size_bytes    bigint NOT NULL,
    page_count         int NOT NULL,
    status             document_status NOT NULL DEFAULT 'processing',
    created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_documents_org_id ON documents(organization_id);
CREATE INDEX idx_documents_uploader_id ON documents(uploaded_by_user_id);

-- =========================================
-- DOCUMENT CHUNKS
-- =========================================

CREATE TABLE document_chunks (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id  uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index  int NOT NULL,
    content      text NOT NULL,
    page_number  int,
    vector_id    varchar(255),        -- id en el vector store (Chroma, pgvector, etc.)
    tokens       int,
    created_at   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_document_chunks_doc_idx UNIQUE (document_id, chunk_index)
);

CREATE INDEX idx_document_chunks_doc_id ON document_chunks(document_id);

-- =========================================
-- CHAT SESSIONS
-- =========================================

CREATE TABLE chat_sessions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title           varchar(255) NOT NULL,
    document_ids    uuid[] DEFAULT '{}',  -- documentos relacionados en la sesión
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_org_id ON chat_sessions(organization_id);

-- =========================================
-- CHAT MESSAGES
-- =========================================

CREATE TABLE chat_messages (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_session_id uuid NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            message_role NOT NULL,
    content         text NOT NULL,
    sources         jsonb,          -- citas de documentos, etc.
    tokens_used     int,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_chat_messages_session_id ON chat_messages(chat_session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);

-- =========================================
-- FLASHCARD DECKS
-- =========================================

CREATE TABLE flashcard_decks (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id uuid REFERENCES documents(id) ON DELETE SET NULL,
    name        varchar(255) NOT NULL,
    card_count  int NOT NULL DEFAULT 0,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_flashcard_decks_user_id ON flashcard_decks(user_id);

-- =========================================
-- FLASHCARDS
-- =========================================

CREATE TABLE flashcards (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    deck_id     uuid NOT NULL REFERENCES flashcard_decks(id) ON DELETE CASCADE,
    question    text NOT NULL,
    answer      text NOT NULL,
    difficulty  flashcard_difficulty NOT NULL DEFAULT 'medium',
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_flashcards_deck_id ON flashcards(deck_id);

-- =========================================
-- STUDY PROGRESS (Rachas / progreso)
-- =========================================

CREATE TABLE study_progress (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    flashcard_id  uuid NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
    last_reviewed timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_study_progress_user_card UNIQUE (user_id, flashcard_id)
);

CREATE INDEX idx_study_progress_user_id ON study_progress(user_id);

-- =========================================
-- API KEYS
-- =========================================

CREATE TABLE api_keys (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash    varchar(255) NOT NULL UNIQUE,
    last_used_at timestamptz
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);

-- =========================================
-- WEBHOOK EVENTS
-- =========================================

CREATE TABLE webhook_events (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    event_type      varchar(100) NOT NULL,
    payload         jsonb NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_webhook_events_org_id ON webhook_events(organization_id);
CREATE INDEX idx_webhook_events_created_at ON webhook_events(created_at);