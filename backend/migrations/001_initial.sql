-- centaur.tools initial schema
-- Requires: PostgreSQL 15+ with pgvector extension

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    email VARCHAR(255),
    avatar_url TEXT,
    bio TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tools
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    problem_statement TEXT NOT NULL,
    repo_url TEXT NOT NULL,
    license VARCHAR(50) NOT NULL DEFAULT 'MIT',
    language VARCHAR(100),
    author_id UUID REFERENCES users(id) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', name), 'A') ||
        setweight(to_tsvector('english', problem_statement), 'B') ||
        setweight(to_tsvector('english', description), 'C')
    ) STORED
);
CREATE INDEX idx_tools_search ON tools USING GIN(search_vector);
CREATE INDEX idx_tools_author ON tools(author_id);
CREATE INDEX idx_tools_created ON tools(created_at DESC);

-- Tags
CREATE TABLE tool_tags (
    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    PRIMARY KEY (tool_id, tag)
);
CREATE INDEX idx_tags_tag ON tool_tags(tag);

-- Embeddings (pgvector)
CREATE TABLE tool_embeddings (
    tool_id UUID PRIMARY KEY REFERENCES tools(id) ON DELETE CASCADE,
    embedding vector(768) NOT NULL,
    model_version VARCHAR(100) NOT NULL DEFAULT 'text-embedding-004',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_embeddings_hnsw ON tool_embeddings
    USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Proximity links
CREATE TABLE proximity_links (
    tool_a_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    tool_b_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    similarity FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (tool_a_id, tool_b_id),
    CHECK (tool_a_id < tool_b_id)
);

-- Fork lineage
CREATE TABLE fork_links (
    parent_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    child_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (parent_id, child_id)
);

-- Votes (usefulness)
CREATE TABLE tool_votes (
    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (tool_id, user_id)
);

-- Prior Art
CREATE TABLE prior_art_nominations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    platform_feature TEXT NOT NULL,
    platform VARCHAR(255) NOT NULL,
    evidence TEXT NOT NULL,
    nominated_by UUID REFERENCES users(id) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    confirmed BOOLEAN DEFAULT FALSE,
    confirmed_at TIMESTAMPTZ
);

CREATE TABLE prior_art_votes (
    nomination_id UUID REFERENCES prior_art_nominations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (nomination_id, user_id)
);

-- Forum
CREATE TABLE forum_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    sort_order INT DEFAULT 0
);

INSERT INTO forum_categories (name, slug, description, sort_order) VALUES
    ('Announcements', 'announcements', 'Official announcements and updates', 0),
    ('Help', 'help', 'Get help with tools or building', 1),
    ('Show & Tell', 'show-and-tell', 'Share what you have built', 2),
    ('Meta & Governance', 'meta', 'Discuss the registry itself, governance, and community direction', 3);

CREATE TABLE forum_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES forum_categories(id) NOT NULL,
    author_id UUID REFERENCES users(id) NOT NULL,
    title VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    is_pinned BOOLEAN DEFAULT FALSE,
    is_locked BOOLEAN DEFAULT FALSE,
    reply_count INT DEFAULT 0,
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_threads_category ON forum_threads(category_id, last_activity_at DESC);

CREATE TABLE forum_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES forum_threads(id) ON DELETE CASCADE,
    author_id UUID REFERENCES users(id) NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tool comments (separate from forum)
CREATE TABLE tool_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    author_id UUID REFERENCES users(id) NOT NULL,
    body TEXT NOT NULL,
    parent_id UUID REFERENCES tool_comments(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_comments_tool ON tool_comments(tool_id, created_at);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    data JSONB DEFAULT '{}',
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_notifications_user ON notifications(user_id, read, created_at DESC);

-- Moderation
CREATE TABLE moderation_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    moderator_id UUID REFERENCES users(id) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
