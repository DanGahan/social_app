# AGENTS.md

This document provides instructions for AI agents to understand and interact with this codebase.

## Project Overview

This project is a social media application with a Python-based backend and frontend.

## Tech Stack

- **Backend**: Python, Flask, SQLAlchemy
- **Frontend**: Python, Django
- **Database**: PostgreSQL (managed via Docker)
- **Containerization**: Docker, Docker Compose
- **Security**: HTTPS/TLS with nginx proxy, JWT authentication
- **File Storage**: Local file storage with secure upload endpoints

## Project Structure

- `backend/`: The Flask API that serves as the application's backend.
  - `app.py`: Main Flask application file with REST API endpoints.
  - `models.py`: SQLAlchemy database models.
  - `requirements.txt`: Backend Python dependencies.
  - `uploads/`: Directory for storing uploaded images.
  - `tests/`: Comprehensive test suite (62 tests) covering all API endpoints.
- `frontend/`: The Django application that serves as the user-facing frontend.
  - `core/`: Core Django app containing:
    - User authentication (registration, login)
    - **Home page with integrated add post functionality**
    - API proxy endpoints for secure backend communication
  - `posts_app/`: Django app for post listing and related functionality.
  - `requirements.txt`: Frontend Python dependencies.
  - `tests/`: Frontend test suite covering UI and API proxy functionality.
- `database/`: Contains the PostgreSQL Dockerfile and initialization script.
- `docker-compose.yml`: Defines services including nginx for HTTPS termination.
- `nginx.conf`: Nginx configuration for SSL/TLS proxy.
- `generate-certs.sh`: Script for generating SSL certificates with LAN IP support.
- `certs/`: Directory for SSL certificates (created by generate-certs.sh).
- `.github/workflows/ci.yml`: GitHub Actions workflow for continuous integration.

## Key Workflows

### Development
- **Running the application**: `docker-compose up`
- **HTTPS setup for camera features**: `./generate-certs.sh` then `docker-compose up`
- **Populating the database**: `docker-compose exec backend python populate_db.py`
- **Container restarts**: `docker-compose restart [service]` (commonly used: `frontend`, `backend`)

### Testing
- **Backend tests**: `docker-compose exec backend python -m pytest tests/ -v` (62 tests)
- **Frontend tests**: `docker-compose exec frontend python manage.py test` (21 tests)
- **Test coverage**: 83 total tests following agile test pyramid principles

### File Upload System
- **Backend endpoint**: `POST /posts/upload` - Handles multipart file uploads
- **Frontend proxy**: `POST /api/posts/upload-image` - Secure session-based proxy
- **File serving**: `GET /uploads/<filename>` - Serves uploaded images
- **Supported formats**: PNG, JPG, JPEG, GIF, HEIC, WEBP

## Add Post Feature Implementation

### Architecture
- **Location**: Integrated into `core/templates/core/home.html` (not a separate page)
- **API Communication**: JavaScript → Frontend Django proxy → Backend Flask API
- **File Handling**: Multipart uploads with secure validation and storage

### Key Components
- **UI Tabs**: Library (default), Camera, URL - in that specific order
- **Camera System**:
  - Supports front/back camera switching (`environment` = back, `user` = front)
  - Capture/retake workflow with image preview replacement
  - Safari-specific compatibility layers and fallbacks
- **Upload Validation**: Client and server-side validation for file types and sizes
- **CSRF Protection**: All forms include proper CSRF token handling

### Browser Compatibility
- **HTTPS Requirement**: Safari requires HTTPS for camera access (`navigator.mediaDevices.getUserMedia()`)
- **Cross-platform**: Tested on iOS Safari, macOS Safari, Chrome
- **Fallback Handling**: Graceful degradation when camera access fails

### Future Agent Notes
- Always test camera functionality with `./generate-certs.sh` for HTTPS
- Use `docker-compose restart frontend` after template/static file changes
- Test coverage must include both UI and API proxy endpoints
- File upload changes require testing both frontend proxy and backend endpoints

## Code Quality

- All new code and features must be accompanied by unit tests.
- Ensure that any changes do not cause a drop in the overall test coverage percentage.
- Camera features require HTTPS testing environment.

## Security

- Before finalizing changes, run dependency scans on both the frontend and backend Docker images to ensure no new vulnerabilities are introduced.
- To check for open code scanning alerts, use the command `gh code-scanning alert list`. If this command fails because the `code-scanning` extension is not installed, use the GitHub API directly: `gh api /repos/DanGahan/social_app/code-scanning/alerts`.
- To check for dependency vulnerabilities (Dependabot alerts), use the command `gh api /repos/DanGahan/social_app/vulnerability-alerts`.

## GitHub Workflow

- All new features must be developed on a dedicated feature branch.
- Merging to the `main` branch requires a Pull Request (PR).
- Regularly check the GitHub repository for security alerts and address them promptly.
- New features and tasks will be tracked as GitHub Issues.
- All interactions with GitHub (e.g., creating PRs, managing issues) should be done using the GitHub CLI (`gh`).

## Agent Instructions

- Adhere to the existing code style and conventions in each service (Flask for backend, Django for frontend).
- When modifying dependencies, update the appropriate `requirements.txt` file.
- For database schema changes, new migrations may be needed.
