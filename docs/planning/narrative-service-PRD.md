# PRD - Narrative Service

## 1. Overview

The Narrative Service is the core engine that drives the dynamic, personalized story experience for Diana Bot users. It is responsible for managing narrative progression, character interactions, story branching, and the long-term consequences of user choices. This service will work in close coordination with the Emotional System and Gamification Service to create a deeply immersive and emotionally resonant journey for the user, orchestrated by Lucien and emotionally interpreted by Diana.

## 2. Goals and Objectives

*   **Primary Goal:** To create a compelling and personalized narrative experience that adapts to user choices and emotional states.
*   **Secondary Goal:** To deepen the user's emotional connection to Diana and Lucien by ensuring their interactions are consistent, meaningful, and impactful.
*   **Business Goal:** To increase user retention and engagement by providing a unique and evolving story that encourages continued interaction.

## 3. User Stories

**EPIC: Narrative Progression**

*   **User Story 1: Starting the Journey**
    *   **As a** new user,
    *   **I want** to be introduced to the central narrative by Lucien in a mysterious and elegant manner,
    *   **so that** I understand the premise of my journey and my role within it.
    *   **Acceptance Criteria:**
        *   Lucien delivers the introductory monologue.
        *   Diana offers a brief, intimate commentary on my arrival.
        *   The system logs the start of the user's narrative journey in the database.

*   **User Story 2: Making a Choice**
    *   **As a** user,
    *   **I want** to be presented with meaningful choices at key narrative moments,
    *   **so that** I feel my decisions have a real impact on the story's direction.
    *   **Acceptance Criteria:**
        *   Lucien presents the context of the choice.
        *   The user is given 2-3 distinct options.
        *   Diana offers a poetic or emotional reflection on the potential paths.
        *   The user's choice is recorded and triggers the corresponding narrative branch.

*   **User Story 3: Experiencing Consequences**
    *   **As a** user,
    *   **I want** to see the consequences of my past decisions reflected in future events and dialogues,
    *   **so that** the story feels coherent and my agency is validated.
    *   **Acceptance Criteria:**
        *   If a user made "Choice A" in a previous chapter, a future event "Event X" occurs.
        *   If they had made "Choice B", "Event Y" occurs instead.
        *   Characters (Diana/Lucien) reference the user's past actions in their dialogue.

*   **User Story 4: Narrative-Driven Gamification**
    *   **As a** user,
    *   **I want** to receive "besitos" for completing significant narrative milestones,
    *   **so that** my story progression feels rewarding and integrated with the gamification system.
    *   **Acceptance Criteria:**
        *   Upon completing a story chapter, the Narrative Service calls the Gamification Service to award a predefined amount of "besitos".
        *   Lucien announces the reward in his characteristic atmospheric style.

## 4. Personality Impact Analysis

This service is critical for maintaining the Diana/Lucien dynamic. The following rules must be enforced:

*   **Lucien as the Narrator:** Lucien's role is to set the stage, explain the stakes, and present the choices. He is the structural guide. The service will use his voice for all objective descriptions of events, locations, and choices. He is the "Dungeon Master."
*   **Diana as the Emotional Resonator:** Diana's role is to provide the internal, emotional commentary on the user's situation. She does not advance the plot but deepens its meaning. The service will trigger her voice after a choice is made, or during a moment of reflection, to comment on the *feeling* of the situation. She is the "Inner Voice."
*   **Dynamic Tension:** The service will ensure their dialogues never overlap in function. Lucien provides the *what*, and Diana provides the *why it matters to you*. For example:
    *   **Lucien:** "Before you are two paths. One leads to the city, bathed in light; the other, to the forest, shrouded in shadow. You must choose."
    *   **User:** (Chooses the forest)
    *   **Diana:** "Of course you chose the darkness... a part of you always seeks the things we're not supposed to see. I wonder what you're hoping to find there... or what you're running from."

## 5. Technical Integration Requirements

*   **Emotional System:**
    *   The Narrative Service MUST read the user's current emotional state (e.g., `curious`, `melancholy`, `agitated`) before generating dialogue.
    *   Dialogue variations for both Diana and Lucien must exist to match the user's emotional state, making the interaction feel more personal.
    *   The outcome of narrative choices MUST be able to trigger a change in the user's emotional state by calling the Emotional System.

*   **Gamification Service ("besitos"):**
    *   The service must have a secure endpoint to call the Gamification Service to award `besitos` to a user.
    *   Specific narrative milestones will have a predefined `besitos` reward.
    *   Future Requirement: Some narrative branches may be locked until a user has accumulated a certain number of `besitos`, requiring the Narrative Service to query the user's balance.

*   **Multi-tenant Database:**
    *   All user-specific narrative data, including their current position in the story, choices made, and unlocked branches, MUST be stored with a `tenant_id` to ensure strict data isolation.
    *   The service's database schema must include a `tenant_id` field in all relevant tables (`narrative_progress`, `user_choices`, etc.).
    *   All database queries must be scoped to the `tenant_id` of the user making the request.

## 6. Edge Cases

*   **Invalid Choice:** If the user provides an input that doesn't match the presented options, Lucien should gently guide them back: "An interesting thought, but the path diverges here. You must choose one of the options before you."
*   **Emotional State Unavailable:** If the Emotional System fails to return a state, the service should default to a "neutral" emotional dialogue path to avoid breaking the user experience.
*   **Service Unavailability:** If a dependent service (e.g., Gamification) is down, the narrative action should still complete. The reward action should be queued and retried later.
*   **Narrative Dead End:** The narrative structure should be designed to avoid true dead ends. Every choice should lead to a continuing story, even if it's a less "optimal" path.

## 7. Success Metrics

*   **Narrative Branching:** A successful implementation will show a healthy distribution of users across different major narrative branches (e.g., not 95% of users choosing the same path every time).
*   **Engagement:** An increase in the average number of interactions per user session.
*   **Completion Rate:** A high percentage of users who start a narrative arc see it through to its conclusion.
*   **User Feedback:** Qualitative feedback from users indicating they feel their choices matter and that the story is emotionally engaging.
