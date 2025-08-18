# Social App

Project to test AI coding assistants, all code AI generated with the odd bit of manual debugging. All content below AI generated.

# Background
The Social App is a platform designed to allow users to connect with each other, share posts, and manage their social interactions. It features user registration, login, profile management, connection requests, and a feed of posts from connected users.

# Front End
The frontend of the Social App is built using **Django**, a high-level Python web framework. It handles user authentication (registration, login), displays the main application interface (home page with posts, connections, and requests), and interacts with the backend API to fetch and send data. Key components include:
*   **`core/` app:** Contains the main views, templates, and URL configurations for the core functionalities like user authentication, home page, and connection management.
*   **`posts_app/` app:** Handles functionalities related to user posts.
*   **Templates (`.html` files):** Define the structure and layout of the web pages, using Django's template language to render dynamic content.
*   **Static files (`.css`, `.js`, images):** Provide styling, client-side interactivity, and visual assets.

# Back End
The backend of the Social App is built using **Flask**, a lightweight Python web framework, and **SQLAlchemy** for Object Relational Mapping (ORM) to interact with the PostgreSQL database. It provides a RESTful API for all data operations, including user management, post management, and connection management.

### API Endpoints

*   **`POST /auth/register`**
    *   **Purpose:** Registers a new user.
    *   **Structure:** Accepts `email` and `password` in the request body. Hashes the password before storing.
    *   **Returns:** User ID on success, or an error if the email already exists or input is invalid.

*   **`POST /auth/login`**
    *   **Purpose:** Authenticates a user and issues a JWT token.
    *   **Structure:** Accepts `email` and `password` in the request body.
    *   **Returns:** A JWT token on successful login, or an error for invalid credentials.

*   **`GET /users/me`**
    *   **Purpose:** Retrieves the profile information of the currently authenticated user.
    *   **Structure:** Requires a valid JWT token in the `x-access-token` header.
    *   **Returns:** User's `user_id`, `email`, `display_name`, `profile_picture_url`, and `bio`.

*   **`GET /users/<int:user_id>/profile`**
    *   **Purpose:** Retrieves the profile information of a specific user by ID.
    *   **Structure:** Requires a valid JWT token.
    *   **Returns:** User's `user_id`, `email`, `display_name`, `profile_picture_url`, and `bio`.

*   **`PUT /users/<int:user_id>/profile`**
    *   **Purpose:** Updates the profile information of the authenticated user.
    *   **Structure:** Requires a valid JWT token. Accepts `display_name`, `profile_picture_url`, and `bio` in the request body.
    *   **Returns:** Success message or error.

*   **`GET /users/search`**
    *   **Purpose:** Searches for users by display name.
    *   **Structure:** Requires a valid JWT token. Accepts a `query` parameter in the URL.
    *   **Returns:** A list of matching users, including their `user_id`, `display_name`, `profile_picture_url`, and flags indicating if they are already connected or have a pending request.

*   **`POST /connections/request`**
    *   **Purpose:** Sends a connection request to another user.
    *   **Structure:** Requires a valid JWT token. Accepts `to_user_id` in the request body.
    *   **Returns:** Success message and `request_id`, or an error if a request/connection already exists.

*   **`POST /connections/accept`**
    *   **Purpose:** Accepts a pending connection request.
    *   **Structure:** Requires a valid JWT token. Accepts `request_id` in the request body.
    *   **Returns:** Success message and `connection_id`, or an error if the request is not found or not for the current user.

*   **`POST /connections/deny`**
    *   **Purpose:** Denies a pending connection request.
    *   **Structure:** Requires a valid JWT token. Accepts `request_id` in the request body.
    *   **Returns:** Success message, or an error if the request is not found or not for the current user.

*   **`GET /users/<int:user_id>/connections`**
    *   **Purpose:** Retrieves a list of connections for a specific user.
    *   **Structure:** Requires a valid JWT token.
    *   **Returns:** A list of connected users' `user_id`, `email`, `display_name`, and `profile_picture_url`.

*   **`GET /users/<int:user_id>/pending_requests`**
    *   **Purpose:** Retrieves pending connection requests received by a user.
    *   **Structure:** Requires a valid JWT token.
    *   **Returns:** A list of pending requests, including `request_id`, `from_user_id`, `from_user_email`, `from_user_display_name`, `from_user_profile_picture_url`, and `created_at`.

*   **`GET /users/<int:user_id>/sent_requests`**
    *   **Purpose:** Retrieves pending connection requests sent by a user.
    *   **Structure:** Requires a valid JWT token.
    *   **Returns:** A list of sent requests, including `request_id`, `to_user_id`, `to_user_email`, `to_user_display_name`, `to_user_profile_picture_url`, and `created_at`.

*   **`GET /users/<int:user_id>/posts`**
    *   **Purpose:** Retrieves posts made by a specific user.
    *   **Structure:** Requires a valid JWT token.
    *   **Returns:** A list of posts, including `post_id`, `caption`, `image_url`, `created_at`, `user_id`, `author_display_name`, and `author_profile_picture_url`.

*   **`GET /users/<int:user_id>/connections/posts`**
    *   **Purpose:** Retrieves posts from the user's connections (and their own posts).
    *   **Structure:** Requires a valid JWT token.
    *   **Returns:** A list of posts from connected users, including post details and author information.

# Database
The database for the Social App is **PostgreSQL**. It is managed using **SQLAlchemy** as an ORM in the backend. The database schema is defined in `backend/models.py` and includes tables for:
*   **`users`**: Stores user information (email, hashed password, display name, profile picture URL, bio).
*   **`posts`**: Stores user posts (caption, image URL, creation timestamp, associated user ID).
*   **`connections`**: Stores established connections between users.
*   **`connection_requests`**: Stores pending connection requests between users, with a status (pending, accepted, denied).

## How to Populate Test Data
To populate the database with test data, follow these steps:
1.  **Ensure Docker containers are running:**
    ```bash
    docker-compose up -d
    ```
2.  **Execute the population script:**
    ```bash
    docker-compose exec backend python populate_db.py
    ```
    This script (`backend/populate_db.py`) will create a set of test users, posts, and connections in the database.