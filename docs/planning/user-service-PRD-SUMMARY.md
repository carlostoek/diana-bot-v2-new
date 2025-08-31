# Executive Summary: User Service PRD

## 1. Core Concept

The User Service is responsible for **zero-friction, automatic user management** within Telegram. Users are registered and authenticated silently and instantly upon their first interaction with the bot. No passwords, no emails, no forms.

**Primary Key:** The user's unique Telegram ID is the single source of truth for identity.

## 2. Key Architectural Components

1.  **`UserRegistrationMiddleware`**: Intercepts *all* incoming Telegram interactions. This is the entry point.
2.  **`UserService`**: Contains the core logic to find or create a user in the database.
3.  **`User` Model**: The SQLAlchemy model representing the user in the database.
4.  **PostgreSQL Database**: The persistence layer.

## 3. Core Data Model (`users` table)

-   `id` (BIGINT, PK): Telegram User ID
-   `first_name` (VARCHAR)
-   `last_name` (VARCHAR, nullable)
-   `username` (VARCHAR, nullable)
-   `role` (VARCHAR, default: 'free')
-   `is_admin` (BOOLEAN, default: false)
-   `created_at` (TIMESTAMP)
-   `updated_at` (TIMESTAMP)

## 4. Critical Requirements

### Functional

-   **Automatic Registration:** Must happen on the very first interaction.
-   **Idempotency:** Multiple interactions from a new user must not create duplicate records.
-   **Role Management:** Must support `free`, `vip`, and `admin` roles.

### Non-Functional

-   **Performance:**
    -   New user registration: **< 100ms**
    -   Existing user lookup: **< 50ms**
-   **Reliability:** The middleware and the bot's core functionality **must continue to operate even if the UserService or database fails** (graceful degradation).

## 5. Character & Design Impact

-   This service is **purely backend**. There is no user-facing UI for registration or login.
-   The user's perception of this process should be non-existent. It just works.
-   The only narrative impact is how Lucien or Diana might address a user by their `first_name`, which this service makes available.

This summary provides the essential information for the next phases of review and implementation.
