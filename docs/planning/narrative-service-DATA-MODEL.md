# Narrative Service - Data Model Design

*This document will contain the database schema and data models for the Narrative Service, as designed by the specialist agent.*

**Status:** IN PROGRESS

**Assigned to:** @sql-pro

---

## 1. Data Model Overview

This PostgreSQL schema is designed to address the core requirements of the Narrative Service, with a strong emphasis on performance and scalability as requested by the architect.

The key design principles are:
1.  **Separation of Content and State:** The narrative's structure (chapters, scenes, etc.) is stored separately from the user's progress. This allows the narrative content to be cached heavily in Redis, minimizing database reads.
2.  **Indexed for Performance:** Foreign keys and frequently queried columns (especially `user_id`) are indexed to ensure fast lookups.
3.  **Flexibility with JSONB:** The use of `JSONB` for storing emotional variables and decision consequences provides flexibility without sacrificing indexing capabilities.

## 2. SQL DDL (PostgreSQL)

Here is the complete Data Definition Language for the service.

```sql
-- Use UUIDs for primary keys to ensure global uniqueness across services
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table to store the high-level narrative chapters
CREATE TABLE narrative_chapters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    sort_order INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table to store individual scenes within a chapter
CREATE TABLE narrative_scenes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chapter_id UUID NOT NULL REFERENCES narrative_chapters(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    dialogue TEXT NOT NULL, -- The core text of the scene
    character_speaker VARCHAR(100), -- e.g., 'Diana', 'Lucien', 'System'
    sort_order INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_scenes_chapter_id ON narrative_scenes(chapter_id);

-- Table to store the possible decisions/choices for a scene
-- A scene can have multiple decisions, leading to different next scenes
CREATE TABLE narrative_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scene_id UUID NOT NULL REFERENCES narrative_scenes(id) ON DELETE CASCADE,
    choice_text VARCHAR(255) NOT NULL,
    next_scene_id UUID REFERENCES narrative_scenes(id) ON DELETE SET NULL, -- The scene this choice leads to
    emotional_variables_impact JSONB, -- e.g., {"affinity_diana": 10, "paradox_level": -5}
    required_conditions JSONB, -- e.g., {"affinity_diana_gt": 50} -> only show if condition is met
    sort_order INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_decisions_scene_id ON narrative_decisions(scene_id);

-- This is the most critical table for performance.
-- It stores the current state of each user's narrative journey.
CREATE TABLE user_narrative_states (
    user_id VARCHAR(255) PRIMARY KEY, -- Assuming user_id is a string from an external service
    current_scene_id UUID NOT NULL REFERENCES narrative_scenes(id),
    emotional_variables JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_states_current_scene_id ON user_narrative_states(current_scene_id);

-- A history log of all decisions made by a user.
-- Useful for analytics, debugging, and fulfilling narrative branching conditions.
CREATE TABLE user_decision_log (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    decision_id UUID NOT NULL REFERENCES narrative_decisions(id),
    scene_id UUID NOT NULL REFERENCES narrative_scenes(id),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_decision_log_user_id ON user_decision_log(user_id);
CREATE INDEX idx_decision_log_decision_id ON user_decision_log(decision_id);

```

## 3. Design Justifications

-   **`user_narrative_states`:** This table is intentionally kept lean. It only stores the *current* state. The `user_id` is the primary key for extremely fast lookups (`WHERE user_id = ?`). Storing emotional variables in a `JSONB` column allows us to add or remove variables in the future without schema migrations.
-   **`user_decision_log`:** By logging every decision, we create a powerful audit trail. This table can answer questions like "Has this user ever chosen decision X?" which is essential for conditional branching, without bloating the main `user_narrative_states` table. It is indexed heavily on `user_id` for quick history lookups.
-   **Content Tables (`chapters`, `scenes`, `decisions`):** These tables are designed to be read-heavy and write-light. They will be updated by admins but read frequently by the application. The architect's recommendation to cache these tables in Redis is strongly endorsed. The entire narrative tree can be loaded into memory to serve requests without hitting the database for every interaction.

This schema provides the required flexibility for the narrative design while being optimized for the high-read, high-write environment of user state management.

---