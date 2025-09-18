# AGENTS.md

This document provides instructions for AI agents to understand and interact with this codebase.

## Project Overview

This project is a social media application with a Python-based backend and frontend.

## Tech Stack

- **Backend**: Python, Flask, SQLAlchemy
- **Frontend**: Python, Django
- **Database**: PostgreSQL (managed via Docker)
- **Containerization**: Docker, Docker Compose

## Project Structure

- `backend/`: The Flask API that serves as the application's backend.
  - `app.py`: Main Flask application file.
  - `models.py`: SQLAlchemy database models.
  - `requirements.txt`: Backend Python dependencies.
  - `uploads/`: Directory for storing uploaded images.
- `frontend/`: The Django application that serves as the user-facing frontend.
  - `core/`: Core Django app for user registration, login, and profiles.
  - `posts_app/`: Django app for creating and viewing posts.
  - `requirements.txt`: Frontend Python dependencies.
- `database/`: Contains the PostgreSQL Dockerfile and initialization script.
- `docker-compose.yml`: Defines and configures the services (backend, frontend, database) for the application.
- `.github/workflows/ci.yml`: GitHub Actions workflow for continuous integration.

## Key Workflows

- **Running the application**: `docker-compose up`
- **Populating the database**: After a container rebuild, run `docker-compose exec backend python populate_db.py` to seed the database with initial data.
- **Running backend tests**: `docker-compose exec backend pytest`
- **Running frontend tests**: `docker-compose exec frontend python manage.py test`
- **Uploading images**: The backend provides a `POST /api/posts/upload-image` endpoint for uploading images.

## Code Quality

- All new code and features must be accompanied by unit tests.
- Ensure that any changes do not cause a drop in the overall test coverage percentage.

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
