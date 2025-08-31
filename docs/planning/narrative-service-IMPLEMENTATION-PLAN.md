# Narrative Service - Implementation Plan

## 1. Overview

This document outlines the development tasks required to build the Narrative Service, based on the approved architecture, data model, and character consistency reviews. The implementation will be executed in phases to ensure a structured and testable workflow.

**Primary Specialists Required:** `@python-pro`, `@test-automator`
**Reviewing Specialist:** `@character-consistency-specialist`

---

## 2. Phase 1: Core Infrastructure & Data Layer

**Objective:** Set up the project foundation and database models.

-   **Task 1.1: Project Scaffolding**
    -   **Description:** Initialize a new FastAPI project. Set up the directory structure, dependencies (`FastAPI`, `SQLAlchemy`, `Alembic`, `Pydantic`), and basic configuration.
    -   **Assigned to:** `@python-pro`

-   **Task 1.2: Database Migrations**
    -   **Description:** Implement the full database schema from `narrative-service-DATA-MODEL.md` using SQLAlchemy models and generate the initial Alembic migration scripts.
    -   **Assigned to:** `@python-pro`

-   **Task 1.3: Implement Character ENUM (Consistency Recommendation #1)**
    -   **Description:** Create the `character_enum` type in PostgreSQL and ensure the `character_speaker` field in the `narrative_scenes` model is strictly typed with this enum.
    -   **Assigned to:** `@python-pro`

---

## 3. Phase 2: Narrative Content Management (Admin API)

**Objective:** Build the backend functionality for creating and managing the narrative.

-   **Task 2.1: CRUD Endpoints for Narrative Structure**
    -   **Description:** Implement the administrative API endpoints for creating, reading, updating, and deleting `Chapters`, `Scenes`, and `Decisions`. These endpoints will be used by the future admin panel.
    -   **Assigned to:** `@python-pro`

-   **Task 2.2: Implement Narrative Linter (Consistency Recommendation #3)**
    -   **Description:** Develop a validation module (the "Narrative Linter") that runs before any narrative content is saved via the admin API. It must check for orphaned scenes, dead-end decisions, and logical contradictions.
    -   **Assigned to:** `@python-pro`

---

## 4. Phase 3: Core Logic & User-Facing API

**Objective:** Implement the engine that drives the user's narrative experience.

-   **Task 3.1: State Management**
    -   **Description:** Implement the logic to manage `user_narrative_states`, including creating a new state, fetching the current state, and updating it based on decisions.
    -   **Assigned to:** `@python-pro`

-   **Task 3.2: Build the Narrative Engine (Consistency Recommendation #2)**
    -   **Description:** This is the core logic. The engine must process a user's decision, evaluate complex `required_conditions` (including checks against the decision log), calculate the `emotional_variables_impact`, and determine the `next_scene_id`.
    -   **Assigned to:** `@python-pro`

-   **Task 3.3: Implement Public API**
    -   **Description:** Expose the primary user-facing endpoints: `POST /start`, `GET /state/{userId}`, and `POST /decision`.
    -   **Assigned to:** `@python-pro`

---

## 5. Phase 4: Integration, Testing & Final Validation

**Objective:** Connect the service to the wider ecosystem and ensure quality.

-   **Task 4.1: Event Publishing & Caching**
    -   **Description:** Implement the `Event Publisher` to send messages to RabbitMQ. Set up Redis caching for the static narrative content tables to optimize performance.
    -   **Assigned to:** `@python-pro`

-   **Task 4.2: Comprehensive Testing**
    -   **Description:** Write unit tests for the Narrative Engine and integration tests for the full API lifecycle. This includes testing edge cases and the Narrative Linter.
    -   **Assigned to:** `@test-automator`

-   **Task 4.3: Final Character Consistency Review**
    -   **Description:** The completed service (running in a staging environment) must be reviewed to ensure the implemented logic and flow possibilities align with the character PRDs.
    -   **Assigned to:** `@character-consistency-specialist`

---

This implementation plan is now the source of truth for the development phase. I will begin by delegating the first set of tasks.
