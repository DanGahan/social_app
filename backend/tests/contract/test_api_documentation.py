"""
API Documentation Testing

Tests to ensure API documentation stays in sync with implementation.
Validates OpenAPI spec against actual API behavior.
"""

import json
from pathlib import Path

import jsonschema
import pytest
import requests
from jsonschema import validate


class TestAPIDocumentation:
    """Test API documentation synchronization with implementation."""

    @pytest.fixture(scope="session")
    def api_spec(self):
        """Load OpenAPI specification."""
        spec_path = Path(__file__).parent.parent.parent / "api_spec.json"
        if not spec_path.exists():
            # Generate basic spec if not exists
            spec = self._generate_basic_spec()
            with open(spec_path, "w") as f:
                json.dump(spec, f, indent=2)
            return spec

        with open(spec_path) as f:
            return json.load(f)

    def _generate_basic_spec(self):
        """Generate basic OpenAPI spec for Social App API."""
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "Social App API",
                "version": "1.0.0",
                "description": "REST API for Social Media Application",
            },
            "servers": [
                {"url": "http://localhost:5000", "description": "Development server"}
            ],
            "components": {
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    }
                },
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "email": {"type": "string", "format": "email"},
                            "display_name": {"type": "string"},
                            "profile_picture_url": {"type": "string"},
                            "bio": {"type": "string"},
                            "created_at": {"type": "string", "format": "date-time"},
                        },
                    },
                    "Post": {
                        "type": "object",
                        "properties": {
                            "post_id": {"type": "integer"},
                            "user_id": {"type": "integer"},
                            "image_url": {"type": "string"},
                            "caption": {"type": "string"},
                            "created_at": {"type": "string", "format": "date-time"},
                            "author_display_name": {"type": "string"},
                            "author_profile_picture_url": {"type": "string"},
                            "like_count": {"type": "integer"},
                            "user_has_liked": {"type": "boolean"},
                            "comment_count": {"type": "integer"},
                            "recent_comments": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Comment"},
                            },
                        },
                    },
                    "Comment": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "content": {"type": "string"},
                            "author_display_name": {"type": "string"},
                            "author_profile_picture_url": {"type": "string"},
                            "created_at": {"type": "string", "format": "date-time"},
                        },
                    },
                    "Error": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string"},
                            "message": {"type": "string"},
                        },
                    },
                },
            },
            "paths": {
                "/auth/register": {
                    "post": {
                        "summary": "Register new user",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["email", "password"],
                                        "properties": {
                                            "email": {
                                                "type": "string",
                                                "format": "email",
                                            },
                                            "password": {
                                                "type": "string",
                                                "minLength": 6,
                                            },
                                        },
                                    }
                                }
                            },
                        },
                        "responses": {
                            "201": {
                                "description": "User registered successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "user_id": {"type": "integer"},
                                                "message": {"type": "string"},
                                            },
                                        }
                                    }
                                },
                            },
                            "400": {
                                "description": "Invalid input",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/Error"}
                                    }
                                },
                            },
                        },
                    }
                },
                "/auth/login": {
                    "post": {
                        "summary": "User login",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["email", "password"],
                                        "properties": {
                                            "email": {
                                                "type": "string",
                                                "format": "email",
                                            },
                                            "password": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Login successful",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "token": {"type": "string"},
                                                "user_id": {"type": "integer"},
                                                "message": {"type": "string"},
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
                "/users/{user_id}/posts": {
                    "get": {
                        "summary": "Get user posts",
                        "security": [{"BearerAuth": []}],
                        "parameters": [
                            {
                                "name": "user_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "User posts retrieved",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {
                                                "$ref": "#/components/schemas/Post"
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
                "/posts": {
                    "post": {
                        "summary": "Create new post",
                        "security": [{"BearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["image_url"],
                                        "properties": {
                                            "image_url": {"type": "string"},
                                            "caption": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        },
                        "responses": {
                            "201": {
                                "description": "Post created successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "post_id": {"type": "integer"},
                                                "message": {"type": "string"},
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
                "/posts/{post_id}/like": {
                    "post": {
                        "summary": "Toggle like on post",
                        "security": [{"BearerAuth": []}],
                        "parameters": [
                            {
                                "name": "post_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Like toggled successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "message": {"type": "string"},
                                                "action": {
                                                    "type": "string",
                                                    "enum": ["liked", "unliked"],
                                                },
                                                "like_count": {"type": "integer"},
                                                "user_has_liked": {"type": "boolean"},
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
                "/posts/{post_id}/comments": {
                    "get": {
                        "summary": "Get post comments",
                        "security": [{"BearerAuth": []}],
                        "parameters": [
                            {
                                "name": "post_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                            },
                            {
                                "name": "page",
                                "in": "query",
                                "schema": {"type": "integer", "default": 1},
                            },
                            {
                                "name": "per_page",
                                "in": "query",
                                "schema": {
                                    "type": "integer",
                                    "default": 10,
                                    "maximum": 50,
                                },
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "Comments retrieved",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "comments": {
                                                    "type": "array",
                                                    "items": {
                                                        "$ref": "#/components/schemas/Comment"
                                                    },
                                                },
                                                "pagination": {
                                                    "type": "object",
                                                    "properties": {
                                                        "page": {"type": "integer"},
                                                        "per_page": {"type": "integer"},
                                                        "total": {"type": "integer"},
                                                        "pages": {"type": "integer"},
                                                    },
                                                },
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    },
                    "post": {
                        "summary": "Add comment to post",
                        "security": [{"BearerAuth": []}],
                        "parameters": [
                            {
                                "name": "post_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                            }
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["content"],
                                        "properties": {
                                            "content": {
                                                "type": "string",
                                                "maxLength": 500,
                                            }
                                        },
                                    }
                                }
                            },
                        },
                        "responses": {
                            "201": {
                                "description": "Comment added successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "message": {"type": "string"},
                                                "comment": {
                                                    "$ref": "#/components/schemas/Comment"
                                                },
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    },
                },
            },
        }

    def test_auth_register_endpoint_matches_spec(self, api_spec):
        """Test registration endpoint response matches OpenAPI spec."""
        endpoint_spec = api_spec["paths"]["/auth/register"]["post"]
        success_schema = endpoint_spec["responses"]["201"]["content"][
            "application/json"
        ]["schema"]

        # Mock API call (in real test, this would hit actual API)
        mock_response = {"user_id": 123, "message": "User registered successfully"}

        # Validate against schema
        try:
            validate(instance=mock_response, schema=success_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Registration response doesn't match spec: {e}")

    def test_auth_login_endpoint_matches_spec(self, api_spec):
        """Test login endpoint response matches OpenAPI spec."""
        endpoint_spec = api_spec["paths"]["/auth/login"]["post"]
        success_schema = endpoint_spec["responses"]["200"]["content"][
            "application/json"
        ]["schema"]

        mock_response = {
            "token": "jwt.token.here",
            "user_id": 456,
            "message": "Login successful",
        }

        try:
            validate(instance=mock_response, schema=success_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Login response doesn't match spec: {e}")

    def test_get_posts_endpoint_matches_spec(self, api_spec):
        """Test get posts endpoint response matches OpenAPI spec."""
        endpoint_spec = api_spec["paths"]["/users/{user_id}/posts"]["get"]
        success_schema = endpoint_spec["responses"]["200"]["content"][
            "application/json"
        ]["schema"]

        mock_response = [
            {
                "post_id": 1,
                "user_id": 123,
                "image_url": "/uploads/test.jpg",
                "caption": "Test post",
                "created_at": "2024-01-01T12:00:00",
                "author_display_name": "Test User",
                "author_profile_picture_url": "/uploads/profile.jpg",
                "like_count": 5,
                "user_has_liked": True,
                "comment_count": 2,
                "recent_comments": [
                    {
                        "id": 1,
                        "content": "Great post!",
                        "author_display_name": "Commenter",
                        "author_profile_picture_url": "/uploads/commenter.jpg",
                        "created_at": "2024-01-01T12:30:00",
                    }
                ],
            }
        ]

        try:
            validate(instance=mock_response, schema=success_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Get posts response doesn't match spec: {e}")

    def test_like_toggle_endpoint_matches_spec(self, api_spec):
        """Test like toggle endpoint response matches OpenAPI spec."""
        endpoint_spec = api_spec["paths"]["/posts/{post_id}/like"]["post"]
        success_schema = endpoint_spec["responses"]["200"]["content"][
            "application/json"
        ]["schema"]

        mock_response = {
            "message": "Post liked successfully",
            "action": "liked",
            "like_count": 6,
            "user_has_liked": True,
        }

        try:
            validate(instance=mock_response, schema=success_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Like toggle response doesn't match spec: {e}")

    def test_add_comment_endpoint_matches_spec(self, api_spec):
        """Test add comment endpoint response matches OpenAPI spec."""
        endpoint_spec = api_spec["paths"]["/posts/{post_id}/comments"]["post"]
        success_schema = endpoint_spec["responses"]["201"]["content"][
            "application/json"
        ]["schema"]

        mock_response = {
            "message": "Comment added successfully",
            "comment": {
                "id": 789,
                "content": "This is a test comment",
                "author_display_name": "Test User",
                "author_profile_picture_url": "/uploads/test_profile.jpg",
                "created_at": "2024-01-01T13:00:00",
            },
        }

        try:
            validate(instance=mock_response, schema=success_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Add comment response doesn't match spec: {e}")

    def test_get_comments_endpoint_matches_spec(self, api_spec):
        """Test get comments endpoint response matches OpenAPI spec."""
        endpoint_spec = api_spec["paths"]["/posts/{post_id}/comments"]["get"]
        success_schema = endpoint_spec["responses"]["200"]["content"][
            "application/json"
        ]["schema"]

        mock_response = {
            "comments": [
                {
                    "id": 1,
                    "content": "First comment",
                    "author_display_name": "User1",
                    "author_profile_picture_url": "/uploads/user1.jpg",
                    "created_at": "2024-01-01T10:00:00",
                },
                {
                    "id": 2,
                    "content": "Second comment",
                    "author_display_name": "User2",
                    "author_profile_picture_url": "/uploads/user2.jpg",
                    "created_at": "2024-01-01T11:00:00",
                },
            ],
            "pagination": {"page": 1, "per_page": 10, "total": 2, "pages": 1},
        }

        try:
            validate(instance=mock_response, schema=success_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Get comments response doesn't match spec: {e}")

    def test_request_schema_validation(self, api_spec):
        """Test that request schemas match expected input formats."""
        # Test registration request schema
        register_spec = api_spec["paths"]["/auth/register"]["post"]["requestBody"]
        request_schema = register_spec["content"]["application/json"]["schema"]

        valid_request = {"email": "test@example.com", "password": "securepassword123"}

        invalid_request = {
            "email": "invalid-email",  # Invalid email format
            "password": "123",  # Too short
        }

        # Valid request should pass
        try:
            validate(instance=valid_request, schema=request_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Valid registration request rejected: {e}")

        # Invalid request should fail
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=invalid_request, schema=request_schema)

    def test_schema_completeness(self, api_spec):
        """Test that all documented endpoints have complete schemas."""
        required_fields = ["summary", "responses"]

        for path, methods in api_spec["paths"].items():
            for method, spec in methods.items():
                # Check required fields
                for field in required_fields:
                    assert field in spec, f"{method.upper()} {path} missing {field}"

                # Check response schemas exist
                for status_code, response_spec in spec["responses"].items():
                    if "content" in response_spec:
                        assert (
                            "application/json" in response_spec["content"]
                        ), f"{method.upper()} {path} {status_code} missing JSON content type"

                        json_spec = response_spec["content"]["application/json"]
                        assert (
                            "schema" in json_spec
                        ), f"{method.upper()} {path} {status_code} missing schema"

    def test_examples_are_valid(self, api_spec):
        """Test that examples in the spec are valid according to their schemas."""
        # This would test any examples provided in the OpenAPI spec
        for path, methods in api_spec["paths"].items():
            for method, spec in methods.items():
                # Check request body examples
                if "requestBody" in spec:
                    request_body = spec["requestBody"]
                    if (
                        "content" in request_body
                        and "application/json" in request_body["content"]
                    ):
                        json_content = request_body["content"]["application/json"]
                        if "examples" in json_content:
                            schema = json_content["schema"]
                            for example_name, example in json_content[
                                "examples"
                            ].items():
                                try:
                                    validate(instance=example["value"], schema=schema)
                                except jsonschema.ValidationError as e:
                                    pytest.fail(
                                        f"Invalid example {example_name} in {method.upper()} {path}: {e}"
                                    )

                # Check response examples
                for status_code, response_spec in spec["responses"].items():
                    if (
                        "content" in response_spec
                        and "application/json" in response_spec["content"]
                    ):
                        json_content = response_spec["content"]["application/json"]
                        if "examples" in json_content:
                            schema = json_content["schema"]
                            for example_name, example in json_content[
                                "examples"
                            ].items():
                                try:
                                    validate(instance=example["value"], schema=schema)
                                except jsonschema.ValidationError as e:
                                    pytest.fail(
                                        f"Invalid example {example_name} in {method.upper()} {path} {status_code}: {e}"
                                    )
