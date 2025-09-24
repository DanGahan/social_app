# Social App

Project to test AI coding assistants, all code AI generated with the odd bit of manual debugging. All content below AI generated.

# Background
The Social App is a platform designed to allow users to connect with each other, share posts, and manage their social interactions. It features user registration, login, profile management, connection requests, and a feed of posts from connected users.

# Front End
The frontend of the Social App is built using **Django**, a high-level Python web framework. It handles user authentication (registration, login), displays the main application interface (home page with posts, connections, and requests), and interacts with the backend API to fetch and send data. Key components include:

*   **`core/` app:** Contains the main views, templates, and URL configurations for the core functionalities including:
    *   User authentication (registration, login)
    *   **Integrated Add Post Interface:** Full-featured post creation with tabbed interface (Library, Camera, URL)
    *   Home page with posts, connections, and requests
    *   **Social Interactions:** Complete likes and comments system with real-time UI updates
    *   API proxy endpoints for secure backend communication
*   **`posts_app/` app:** Handles functionalities related to user posts and post listing.
*   **Templates (`.html` files):** Define the structure and layout of the web pages, using Django's template language to render dynamic content.
*   **Static files (`.css`, `.js`, images):** Provide styling, client-side interactivity, and visual assets.

## Add Post Feature
The add post functionality is integrated into the home page with a comprehensive interface supporting multiple upload methods:

### Upload Methods
*   **Library Upload:** File selection from device storage with preview functionality
*   **Camera Capture:** Live camera access with front/back camera switching and capture/retake workflow
*   **URL Input:** Direct image URL entry with validation

### Key Features
*   **Responsive Design:** Full-width image previews matching post display size
*   **Camera Functionality:**
    *   HTTPS support for Safari compatibility
    *   Front/back camera switching
    *   Live preview with capture/retake workflow
    *   Cross-platform support (iOS Safari, macOS Safari, Chrome)
*   **File Validation:** Client-side validation for supported image formats (PNG, JPG, JPEG, GIF, HEIC, WEBP)
*   **Caption System:** 140-character limit with real-time counter
*   **UI Polish:** Consistent styling with black buttons, proper alignment, and intuitive workflows

### Security Features
*   **CSRF Protection:** Full CSRF token integration
*   **HTTPS Support:** Complete SSL/TLS infrastructure for secure camera access
*   **Token-based Authentication:** All API calls properly authenticated
*   **File Upload Security:** Secure file handling and validation

## Social Interactions Feature
The application includes a complete social interaction system allowing users to engage with posts:

### Likes System
*   **Toggle Functionality:** Click heart icon to like/unlike posts
*   **Visual Feedback:** Filled (♥) vs outline (♡) heart icons with like counts
*   **Optimistic Updates:** Immediate UI feedback with server synchronization
*   **Cross-tab Support:** Works seamlessly on both Posts and My Posts tabs

### Comments System
*   **Real-time Commenting:** Add comments with immediate display
*   **Pagination Support:** View all comments with efficient loading
*   **Content Validation:** 500 character limit with client-side validation
*   **Author Attribution:** Comments show author profile pictures and display names
*   **Input Methods:** Submit via Enter key or Post button

### Privacy & Security
*   **Connection-based Access:** Only connections can like/comment on posts
*   **Authentication Required:** All interactions require valid JWT tokens
*   **Data Validation:** Server-side validation for all comment content
*   **Unique Element IDs:** Resolved duplicate ID issues for reliable tab-specific interactions

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
    *   **Structure:** Requires a valid JWT token. Accepts `to_user_id` in the request body.
    *   **Returns:** A list of sent requests, including `request_id`, `to_user_id`, `to_user_email`, `to_user_display_name`, `to_user_profile_picture_url`, and `created_at`.

*   **`POST /posts/upload`**
    *   **Purpose:** Uploads an image file for use in posts.
    *   **Structure:** Requires a valid JWT token. Accepts multipart/form-data with a `file` field containing the image.
    *   **Returns:** Success message and filename URL (`/uploads/filename`) or error for invalid file types.

*   **`POST /posts`**
    *   **Purpose:** Creates a new post.
    *   **Structure:** Requires a valid JWT token. Accepts `image_url` and `caption` in the request body.
    *   **Returns:** Success message and `post_id`, or error for missing fields.

*   **`GET /uploads/<filename>`**
    *   **Purpose:** Serves uploaded image files.
    *   **Structure:** No authentication required for public access to uploaded images.
    *   **Returns:** The image file content with appropriate content-type headers.

*   **`GET /users/<int:user_id>/posts`**
    *   **Purpose:** Retrieves posts made by a specific user.
    *   **Structure:** Requires a valid JWT token.
    *   **Returns:** A list of posts, including `post_id`, `caption`, `image_url`, `created_at`, `user_id`, `author_display_name`, and `author_profile_picture_url`.

*   **`GET /users/<int:user_id>/connections/posts`**
    *   **Purpose:** Retrieves posts from the user's connections (and their own posts).
    *   **Structure:** Requires a valid JWT token.
    *   **Returns:** A list of posts from connected users, including post details and author information.

### Social Interaction Endpoints

*   **`POST /posts/<int:post_id>/like`**
    *   **Purpose:** Toggles like status for a post (like if not liked, unlike if already liked).
    *   **Structure:** Requires a valid JWT token. Connection to post author required.
    *   **Returns:** Success message, like action ("liked"/"unliked"), current like count, and user's like status.

*   **`GET /posts/<int:post_id>/likes`**
    *   **Purpose:** Retrieves like information for a specific post.
    *   **Structure:** Requires a valid JWT token. Connection to post author required.
    *   **Returns:** Post ID, current like count, and whether current user has liked the post.

*   **`POST /posts/<int:post_id>/comments`**
    *   **Purpose:** Adds a new comment to a post.
    *   **Structure:** Requires a valid JWT token. Accepts `content` in request body. Connection to post author required.
    *   **Returns:** Success message and comment details including ID, content, author info, and timestamp.

*   **`GET /posts/<int:post_id>/comments`**
    *   **Purpose:** Retrieves comments for a post with pagination.
    *   **Structure:** Requires a valid JWT token. Optional query parameters: `page` (default 1), `per_page` (default 10, max 50).
    *   **Returns:** List of comments with author details and pagination metadata (total count, pages, current page).

*   **`DELETE /comments/<int:comment_id>`**
    *   **Purpose:** Deletes a comment (only by comment author).
    *   **Structure:** Requires a valid JWT token. User must be the comment author.
    *   **Returns:** Success message confirming deletion.

## Frontend API Proxy Endpoints
The Django frontend provides secure proxy endpoints that handle authentication and forward requests to the Flask backend:

### Post Management
*   **`POST /api/posts/upload-image`** - Proxies file uploads to backend with session authentication
*   **`POST /api/posts/create`** - Proxies post creation with JSON data validation
*   **`GET /uploads/<filename>`** - Serves uploaded images from backend storage

### Social Interactions
*   **`POST /api/posts/<int:post_id>/like`** - Proxies like toggle requests with session token authentication
*   **`POST /api/posts/<int:post_id>/comments`** - Proxies comment creation with JSON data validation
*   **`GET /api/posts/<int:post_id>/comments`** - Proxies comment retrieval with pagination support

## HTTPS Infrastructure
The application includes complete HTTPS support for secure camera access:

*   **Certificate Generation:** Automated SSL certificate creation with LAN IP support
*   **Nginx Proxy:** SSL termination and request forwarding to Django frontend
*   **CSRF Protection:** Trusted origins configuration for HTTPS domains
*   **Cross-device Testing:** Support for iPhone/iPad testing over HTTPS on same LAN

# Database
The database for the Social App is **PostgreSQL**. It is managed using **SQLAlchemy** as an ORM in the backend. The database schema is defined in `backend/models.py` and includes tables for:
*   **`users`**: Stores user information (email, hashed password, display name, profile picture URL, bio).
*   **`posts`**: Stores user posts (caption, image URL, creation timestamp, associated user ID).
*   **`connections`**: Stores established connections between users.
*   **`connection_requests`**: Stores pending connection requests between users, with a status (pending, accepted, denied).
*   **`likes`**: Stores user likes on posts with unique constraint preventing duplicate likes.
*   **`comments`**: Stores user comments on posts with content, timestamps, and author references.

## Setup and Running

### Standard Setup
1.  **Start all services:**
    ```bash
    docker-compose up -d
    ```
2.  **Populate test data:**
    ```bash
    docker-compose exec backend python populate_db.py
    ```
3.  **Access the application:** http://localhost:8000

### HTTPS Setup (Required for Camera Features)
For full camera functionality on Safari and cross-device testing:

1.  **Generate SSL certificates:**
    ```bash
    ./generate-certs.sh
    ```
    This creates self-signed certificates with your local IP address for LAN testing.

2.  **Start services with HTTPS:**
    ```bash
    docker-compose up -d
    ```
    The nginx service automatically provides HTTPS on port 8000.

3.  **Access securely:** https://localhost:8000 or https://[YOUR-LAN-IP]:8000

### Testing
*   **Backend tests:** `docker-compose exec backend python -m pytest tests/ -v`
*   **Frontend tests:** `docker-compose exec frontend python manage.py test`
*   **Test coverage:** 50+ comprehensive tests covering:
    *   Upload, camera, and UI functionality
    *   Likes and comments API endpoints
    *   Social interaction proxy endpoints
    *   Authentication and authorization
    *   Database relationships and constraints

### Camera Features Requirements
*   **HTTPS:** Required for camera access on Safari browsers
*   **Permissions:** Browser will prompt for camera access on first use
*   **Cross-device:** iPhone/iPad testing supported over HTTPS on same LAN
