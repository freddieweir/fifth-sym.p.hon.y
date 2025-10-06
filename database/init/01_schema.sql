-- Fifth Symphony Database Schema
-- PostgreSQL 18

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For fuzzy text search

-- Memories table - Core knowledge base
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT NOT NULL,
    category VARCHAR(50), -- e.g., 'personal', 'technical', 'project', 'anime'
    tags TEXT[], -- Array of tags for categorization
    source VARCHAR(100), -- e.g., 'chat_export', 'manual', 'anilist'
    importance INT DEFAULT 5 CHECK (importance >= 1 AND importance <= 10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}' -- Flexible metadata storage
);

-- Indexes for memories
CREATE INDEX idx_memories_category ON memories(category);
CREATE INDEX idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX idx_memories_importance ON memories(importance DESC);
CREATE INDEX idx_memories_content_search ON memories USING GIN(to_tsvector('english', content));

-- Voice IDs table - ElevenLabs voice configurations
CREATE TABLE voice_ids (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    elevenlabs_voice_id VARCHAR(100) NOT NULL,
    description TEXT,
    personality_traits TEXT[],
    use_case VARCHAR(50), -- e.g., 'orchestrator', 'narrator', 'assistant'
    settings JSONB DEFAULT '{}', -- Voice settings (stability, similarity_boost, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Anime preferences table - AniList data
CREATE TABLE anime_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    anilist_id INT UNIQUE,
    title VARCHAR(255) NOT NULL,
    title_english VARCHAR(255),
    title_romaji VARCHAR(255),
    status VARCHAR(50), -- 'WATCHING', 'COMPLETED', 'PLANNING', etc.
    score INT CHECK (score >= 0 AND score <= 100),
    progress INT DEFAULT 0,
    episodes INT,
    genres TEXT[],
    tags TEXT[],
    notes TEXT,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Indexes for anime
CREATE INDEX idx_anime_status ON anime_preferences(status);
CREATE INDEX idx_anime_score ON anime_preferences(score DESC);
CREATE INDEX idx_anime_genres ON anime_preferences USING GIN(genres);

-- Chat exports table - Processed chat logs
CREATE TABLE chat_exports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    export_date DATE,
    message_count INT,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    adhd_md_path VARCHAR(500), -- Path to Attention-friendly markdown
    llm_txt_path VARCHAR(500), -- Path to LLM-optimized text
    source_json_hash VARCHAR(64), -- SHA256 hash of source JSON
    metadata JSONB DEFAULT '{}'
);

-- Chat messages table - Individual messages from exports
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    export_id UUID REFERENCES chat_exports(id) ON DELETE CASCADE,
    message_number INT NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE,
    has_thinking BOOLEAN DEFAULT FALSE,
    thinking_content TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Indexes for chat messages
CREATE INDEX idx_chat_messages_export ON chat_messages(export_id);
CREATE INDEX idx_chat_messages_role ON chat_messages(role);
CREATE INDEX idx_chat_messages_timestamp ON chat_messages(timestamp DESC);
CREATE INDEX idx_chat_messages_content_search ON chat_messages USING GIN(to_tsvector('english', content));

-- AI personalities table - Forge-created personas
CREATE TABLE ai_personalities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    voice_id UUID REFERENCES voice_ids(id),
    system_prompt TEXT NOT NULL,
    personality_traits JSONB DEFAULT '{}',
    example_conversations JSONB DEFAULT '[]',
    anime_influences TEXT[], -- Anime characters/shows that inspired this personality
    forge_config JSONB DEFAULT '{}', -- Configuration from forge repo
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes for AI personalities
CREATE INDEX idx_ai_personalities_active ON ai_personalities(is_active);

-- Knowledge tags table - Tag taxonomy
CREATE TABLE knowledge_tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag_name VARCHAR(50) NOT NULL UNIQUE,
    parent_tag_id UUID REFERENCES knowledge_tags(id),
    description TEXT,
    color VARCHAR(7), -- Hex color for UI
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Memory associations - Link memories to chat messages, anime, etc.
CREATE TABLE memory_associations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    associated_type VARCHAR(50) NOT NULL, -- 'chat_message', 'anime', 'personality'
    associated_id UUID NOT NULL,
    relevance_score DECIMAL(3, 2) CHECK (relevance_score >= 0 AND relevance_score <= 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for associations
CREATE INDEX idx_memory_assoc_memory ON memory_associations(memory_id);
CREATE INDEX idx_memory_assoc_type ON memory_associations(associated_type, associated_id);

-- Updated timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER update_memories_updated_at BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_voice_ids_updated_at BEFORE UPDATE ON voice_ids
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_ai_personalities_updated_at BEFORE UPDATE ON ai_personalities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Views for common queries

-- Recent memories view
CREATE VIEW recent_memories AS
SELECT id, content, category, tags, importance, created_at
FROM memories
ORDER BY created_at DESC
LIMIT 100;

-- High importance memories
CREATE VIEW important_memories AS
SELECT id, content, category, tags, importance, created_at
FROM memories
WHERE importance >= 8
ORDER BY importance DESC, created_at DESC;

-- Active personalities with voice info
CREATE VIEW active_personalities AS
SELECT
    p.id,
    p.name,
    p.description,
    v.name AS voice_name,
    v.elevenlabs_voice_id,
    p.personality_traits,
    p.anime_influences
FROM ai_personalities p
LEFT JOIN voice_ids v ON p.voice_id = v.id
WHERE p.is_active = TRUE
ORDER BY p.name;

-- Anime watch status summary
CREATE VIEW anime_status_summary AS
SELECT
    status,
    COUNT(*) as count,
    AVG(score) as avg_score
FROM anime_preferences
WHERE score IS NOT NULL
GROUP BY status
ORDER BY count DESC;
