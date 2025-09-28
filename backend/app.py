"""Flask backend application for social media platform."""

import datetime
import logging
import os
import sys
import uuid
from functools import wraps

import jwt
from flask import Flask, jsonify, request, send_from_directory
from sqlalchemy import create_engine, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from config import Config
from models import (
    Base,
    Comment,
    Connection,
    ConnectionRequest,
    Like,
    Notification,
    Post,
    User,
)

app = Flask(__name__)
app.config.from_object(Config)

# Configure logging to stdout
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

# Database setup
engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
Session = sessionmaker(bind=engine)
session = Session()

# Create tables if they don't exist (for development purposes)
Base.metadata.create_all(engine)


def token_required(f):
    """Decorator to require JWT token authentication for API endpoints."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "x-access-token" in request.headers:
            token = request.headers["x-access-token"]
        if not token:
            return jsonify({"message": "Token is missing!"}), 401
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = session.query(User).filter_by(id=data["user_id"]).first()
            if not current_user:
                return jsonify({"message": "User not found!"}), 401
        except Exception:
            return jsonify({"message": "Token is invalid!"}), 401
        return f(current_user, *args, **kwargs)

    return decorated


def create_notification(user_id, actor_user_id, notification_type, post_id=None):
    """Create a notification for a user."""
    try:
        # Get actor user details for message formatting
        actor_user = session.query(User).filter_by(id=actor_user_id).first()
        if not actor_user:
            app.logger.error(f"Actor user {actor_user_id} not found for notification")
            return

        actor_name = actor_user.display_name or actor_user.email

        # Generate message and target URL based on notification type
        if notification_type == "post_liked":
            message = f"{actor_name} liked your post"
            target_url = f"/posts/{post_id}"
        elif notification_type == "post_commented":
            message = f"{actor_name} commented on your post"
            target_url = f"/posts/{post_id}"
        elif notification_type == "connection_request":
            message = f"{actor_name} has requested a connection"
            target_url = "/connections"
        elif notification_type == "connection_accepted":
            message = f"{actor_name} accepted your connection request"
            target_url = "/connections"
        else:
            app.logger.error(f"Unknown notification type: {notification_type}")
            return

        # Create the notification
        notification = Notification(
            user_id=user_id,
            actor_user_id=actor_user_id,
            type=notification_type,
            post_id=post_id,
            message=message,
            target_url=target_url,
            is_read=False,
        )

        session.add(notification)
        session.commit()
        app.logger.debug(
            f"Created notification: {notification_type} for user {user_id}"
        )

    except Exception as e:
        session.rollback()
        app.logger.error(f"Failed to create notification: {e}")


@app.route("/users/me", methods=["GET"])
@token_required
def get_current_user(current_user):
    """Get current user information endpoint."""
    return (
        jsonify(
            {
                "user_id": current_user.id,
                "email": current_user.email,
                "display_name": current_user.display_name,
                "profile_picture_url": current_user.profile_picture_url,
                "bio": current_user.bio,
            }
        ),
        200,
    )


@app.route("/users/<int:user_id>/profile", methods=["GET"])
@token_required
def get_user_profile(current_user, user_id):
    """Get user profile information endpoint."""
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    return (
        jsonify(
            {
                "user_id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "profile_picture_url": user.profile_picture_url,
                "bio": user.bio,
            }
        ),
        200,
    )


@app.route("/users/search", methods=["GET"])
@token_required
def search_users(current_user):
    """Search for users by name endpoint."""
    query = request.args.get("query", "")
    app.logger.debug(f"Search query: {query}")
    if not query:
        return jsonify([]), 200

    users = (
        session.query(User)
        .filter(User.display_name.ilike(f"%{query}%"), User.id != current_user.id)
        .all()
    )
    app.logger.debug(f"Found users: {users}")

    # Get all connections for the current user
    connections = (
        session.query(Connection)
        .filter(
            or_(
                Connection.user_id1 == current_user.id,
                Connection.user_id2 == current_user.id,
            )
        )
        .all()
    )
    connected_user_ids = []
    for conn in connections:
        if conn.user_id1 == current_user.id:
            connected_user_ids.append(conn.user_id2)
        else:
            connected_user_ids.append(conn.user_id1)

    # Get all pending requests for the current user
    pending_requests = (
        session.query(ConnectionRequest)
        .filter(
            or_(
                ConnectionRequest.from_user_id == current_user.id,
                ConnectionRequest.to_user_id == current_user.id,
            ),
            ConnectionRequest.status == "pending",
        )
        .all()
    )
    pending_request_user_ids = set()
    for req in pending_requests:
        if req.from_user_id == current_user.id:
            pending_request_user_ids.add(req.to_user_id)
        else:
            pending_request_user_ids.add(req.from_user_id)

    users_data = [
        {
            "user_id": user.id,
            "display_name": user.display_name,
            "profile_picture_url": user.profile_picture_url,
            "is_connection": user.id in connected_user_ids,
            "has_pending_request": user.id in pending_request_user_ids,
        }
        for user in users
    ]
    app.logger.debug(f"Returning users_data: {users_data}")

    return jsonify(users_data), 200


@app.route("/connections/request", methods=["POST"])
@token_required
def request_connection(current_user):
    data = request.get_json()
    to_user_id = data.get("to_user_id")

    app.logger.debug(
        f"DEBUG: Requesting connection from {current_user.id} to {to_user_id}"
    )

    if not to_user_id:
        return jsonify({"message": "to_user_id is required"}), 400

    if current_user.id == to_user_id:
        return (
            jsonify({"message": "Cannot send connection request to yourself"}),
            400,
        )

    # Determine the ordered user IDs for the connection
    u1_id = min(current_user.id, to_user_id)
    u2_id = max(current_user.id, to_user_id)

    # Check if a connection already exists
    existing_connection = (
        session.query(Connection).filter_by(user_id1=u1_id, user_id2=u2_id).first()
    )
    if existing_connection:
        app.logger.debug(
            f"DEBUG: Existing connection found: "
            f"user1={existing_connection.user_id1}, "
            f"user2={existing_connection.user_id2}"
        )
        return jsonify({"message": "Already connected with this user"}), 409

    new_request = ConnectionRequest(
        from_user_id=current_user.id, to_user_id=to_user_id, status="pending"
    )
    try:
        session.add(new_request)
        session.commit()

        # Create notification for the recipient
        create_notification(
            user_id=to_user_id,
            actor_user_id=current_user.id,
            notification_type="connection_request",
        )

        return (
            jsonify(
                {
                    "message": "Connection request sent successfully",
                    "request_id": new_request.id,
                }
            ),
            201,
        )
    except IntegrityError:
        session.rollback()
        return (
            jsonify({"message": "Connection request already exists or similar issue."}),
            409,
        )
    except Exception as e:
        session.rollback()
        app.logger.error(f"Error sending connection request: {e}")
        return (
            jsonify(
                {"message": "An error occurred while sending the connection request."}
            ),
            500,
        )


@app.route("/auth/register", methods=["POST"])
def register_user():
    """Handle user registration endpoint."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    if session.query(User).filter_by(email=email).first():
        return jsonify({"message": "User with this email already exists"}), 409

    hashed_password = generate_password_hash(password)
    new_user = User(email=email, password_hash=hashed_password)
    session.add(new_user)
    session.commit()

    return (
        jsonify({"message": "User registered successfully", "user_id": new_user.id}),
        201,
    )


@app.route("/auth/login", methods=["POST"])
def login_user():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    user = session.query(User).filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"message": "Invalid credentials"}), 401

    token = jwt.encode(
        {
            "user_id": user.id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
        },
        app.config["SECRET_KEY"],
        algorithm="HS256",
    )

    return jsonify({"message": "Login successful", "token": token}), 200


@app.route("/connections/accept", methods=["POST"])
@token_required
def accept_connection(current_user):
    data = request.get_json()
    request_id = data.get("request_id")

    if not request_id:
        return jsonify({"message": "request_id is required"}), 400

    connection_request = (
        session.query(ConnectionRequest)
        .filter_by(id=request_id, to_user_id=current_user.id, status="pending")
        .first()
    )

    if not connection_request:
        return (
            jsonify({"message": "Pending connection request not found"}),
            404,
        )

    # Create mutual connection
    user_id1 = min(connection_request.from_user_id, connection_request.to_user_id)
    user_id2 = max(connection_request.from_user_id, connection_request.to_user_id)

    new_connection = Connection(user_id1=user_id1, user_id2=user_id2)
    session.add(new_connection)

    # Update request status
    connection_request.status = "accepted"
    session.commit()

    # Create notification for the requester
    create_notification(
        user_id=connection_request.from_user_id,
        actor_user_id=current_user.id,
        notification_type="connection_accepted",
    )

    return (
        jsonify(
            {
                "message": "Connection accepted successfully",
                "connection_id": new_connection.id,
            }
        ),
        200,
    )


@app.route("/connections/deny", methods=["POST"])
@token_required
def deny_connection_request(current_user):
    data = request.get_json()
    request_id = data.get("request_id")

    if not request_id:
        return jsonify({"message": "request_id is required"}), 400

    try:
        connection_request = (
            session.query(ConnectionRequest)
            .filter_by(id=request_id, to_user_id=current_user.id, status="pending")
            .first()
        )

        if not connection_request:
            return (
                jsonify(
                    {
                        "message": "Pending connection request not found or not for this user"
                    }
                ),
                404,
            )

        connection_request.status = "denied"
        session.commit()
        return (
            jsonify({"message": "Connection request denied successfully"}),
            200,
        )
    except Exception as e:
        session.rollback()
        app.logger.error(f"Error denying connection request: {e}")
        return (
            jsonify(
                {"message": "An error occurred while denying the connection request."}
            ),
            500,
        )


@app.route("/users/<int:user_id>/connections", methods=["GET"])
@token_required
def get_user_connections(current_user, user_id):
    if current_user.id != user_id:
        return (
            jsonify({"message": "Cannot access other user's connections!"}),
            403,
        )

    connections = (
        session.query(Connection)
        .filter(or_(Connection.user_id1 == user_id, Connection.user_id2 == user_id))
        .all()
    )

    connected_users = []
    for conn in connections:
        if conn.user_id1 == user_id:
            connected_user = session.query(User).filter_by(id=conn.user_id2).first()
            connected_users.append(
                {
                    "user_id": conn.user_id2,
                    "email": connected_user.email,
                    "display_name": connected_user.display_name,
                    "profile_picture_url": connected_user.profile_picture_url,
                }
            )
        else:
            connected_user = session.query(User).filter_by(id=conn.user_id1).first()
            connected_users.append(
                {
                    "user_id": conn.user_id1,
                    "email": connected_user.email,
                    "display_name": connected_user.display_name,
                    "profile_picture_url": connected_user.profile_picture_url,
                }
            )

    return jsonify(connected_users), 200


@app.route("/users/<int:user_id>/pending_requests", methods=["GET"])
@token_required
def get_pending_requests(current_user, user_id):
    if current_user.id != user_id:
        return (
            jsonify({"message": "Cannot access other user's pending requests!"}),
            403,
        )

    pending_requests = (
        session.query(ConnectionRequest)
        .filter_by(to_user_id=user_id, status="pending")
        .all()
    )

    requests_data = []
    for req in pending_requests:
        from_user = session.query(User).filter_by(id=req.from_user_id).first()
        requests_data.append(
            {
                "request_id": req.id,
                "from_user_id": req.from_user_id,
                "from_user_email": from_user.email,
                "from_user_display_name": from_user.display_name,
                "from_user_profile_picture_url": from_user.profile_picture_url,
                "created_at": req.created_at.isoformat(),
            }
        )

    return jsonify(requests_data), 200


@app.route("/users/<int:user_id>/sent_requests", methods=["GET"])
@token_required
def get_sent_requests(current_user, user_id):
    if current_user.id != user_id:
        return (
            jsonify({"message": "Cannot access other user's sent requests!"}),
            403,
        )

    sent_requests = (
        session.query(ConnectionRequest)
        .filter_by(from_user_id=user_id, status="pending")
        .all()
    )

    requests_data = []
    for req in sent_requests:
        to_user = session.query(User).filter_by(id=req.to_user_id).first()
        requests_data.append(
            {
                "request_id": req.id,
                "to_user_id": req.to_user_id,
                "to_user_email": to_user.email,
                "to_user_display_name": to_user.display_name,
                "to_user_profile_picture_url": to_user.profile_picture_url,
                "created_at": req.created_at.isoformat(),
            }
        )

    return jsonify(requests_data), 200


@app.route("/users/<int:user_id>/posts", methods=["GET"])
@token_required
def get_user_posts(current_user, user_id):
    if current_user.id != user_id:
        return jsonify({"message": "Cannot access other user's posts!"}), 403

    posts = (
        session.query(Post)
        .filter_by(user_id=user_id)
        .order_by(Post.created_at.desc())
        .all()
    )

    posts_data = []
    for post in posts:
        # Get like information
        like_count = session.query(Like).filter_by(post_id=post.id).count()
        user_has_liked = bool(
            session.query(Like)
            .filter_by(user_id=current_user.id, post_id=post.id)
            .first()
        )

        # Get comment information
        comment_count = session.query(Comment).filter_by(post_id=post.id).count()
        recent_comments = (
            session.query(Comment)
            .filter_by(post_id=post.id)
            .order_by(Comment.created_at.asc())
            .limit(3)
            .all()
        )

        recent_comments_data = []
        for comment in recent_comments:
            comment_user = session.query(User).filter_by(id=comment.user_id).first()
            recent_comments_data.append(
                {
                    "id": comment.id,
                    "content": comment.content,
                    "created_at": comment.created_at.isoformat(),
                    "author_display_name": comment_user.display_name,
                    "author_profile_picture_url": comment_user.profile_picture_url,
                }
            )

        posts_data.append(
            {
                "post_id": post.id,
                "caption": post.caption,
                "image_url": post.image_url,
                "created_at": post.created_at.isoformat(),
                "user_id": post.user_id,
                "author_display_name": current_user.display_name,
                "author_profile_picture_url": current_user.profile_picture_url,
                "like_count": like_count,
                "user_has_liked": user_has_liked,
                "comment_count": comment_count,
                "recent_comments": recent_comments_data,
            }
        )
    return jsonify(posts_data), 200


@app.route("/users/<int:user_id>/connections/posts", methods=["GET"])
@token_required
def get_connections_posts(current_user, user_id):
    if current_user.id != user_id:
        return (
            jsonify({"message": "Cannot access other user's connections' posts!"}),
            403,
        )

    # Get connected user IDs
    connections = (
        session.query(Connection)
        .filter(or_(Connection.user_id1 == user_id, Connection.user_id2 == user_id))
        .all()
    )

    connected_user_ids = []
    for conn in connections:
        if conn.user_id1 == user_id:
            connected_user_ids.append(conn.user_id2)
        else:
            connected_user_ids.append(conn.user_id1)

    # Include current user's posts as well, as is common in social feeds
    connected_user_ids.append(user_id)
    connected_user_ids = list(set(connected_user_ids))  # Remove duplicates

    # Fetch posts from connected users (and current user)
    posts = (
        session.query(Post)
        .filter(Post.user_id.in_(connected_user_ids))
        .order_by(Post.created_at.desc())
        .all()
    )

    posts_data = []
    for post in posts:
        # Fetch user details for each post
        post_user = session.query(User).filter_by(id=post.user_id).first()

        # Defensive check: if post_user is None, provide default or skip
        if not post_user:
            continue  # Skip to the next post

        # Get like information
        like_count = session.query(Like).filter_by(post_id=post.id).count()
        user_has_liked = bool(
            session.query(Like)
            .filter_by(user_id=current_user.id, post_id=post.id)
            .first()
        )

        # Get comment information
        comment_count = session.query(Comment).filter_by(post_id=post.id).count()
        recent_comments = (
            session.query(Comment)
            .filter_by(post_id=post.id)
            .order_by(Comment.created_at.asc())
            .limit(3)
            .all()
        )

        recent_comments_data = []
        for comment in recent_comments:
            comment_user = session.query(User).filter_by(id=comment.user_id).first()
            recent_comments_data.append(
                {
                    "id": comment.id,
                    "content": comment.content,
                    "created_at": comment.created_at.isoformat(),
                    "author_display_name": comment_user.display_name,
                    "author_profile_picture_url": comment_user.profile_picture_url,
                }
            )

        posts_data.append(
            {
                "post_id": post.id,
                "caption": post.caption,
                "image_url": post.image_url,
                "created_at": post.created_at.isoformat(),
                "user_id": post.user_id,
                "author_display_name": post_user.display_name,
                "author_profile_picture_url": post_user.profile_picture_url,
                "like_count": like_count,
                "user_has_liked": user_has_liked,
                "comment_count": comment_count,
                "recent_comments": recent_comments_data,
            }
        )
    return jsonify(posts_data), 200


UPLOAD_FOLDER = "./uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "heic", "webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if file has an allowed extension and validate basic security."""
    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def get_safe_extension(original_filename):
    """Extract and validate file extension, returning a safe extension or raising error."""
    if not original_filename or "." not in original_filename:
        raise ValueError("Invalid filename")

    # Get the file extension
    user_extension = original_filename.rsplit(".", 1)[1].lower()

    # Map user extensions to safe, predefined extensions
    # This breaks the data flow by using only predefined safe values
    safe_extension_map = {
        "png": "png",
        "jpg": "jpg",
        "jpeg": "jpg",  # Normalize jpeg to jpg
        "gif": "gif",
        "heic": "heic",
        "webp": "webp",
    }

    if user_extension not in safe_extension_map:
        raise ValueError("File type not allowed")

    # Return the safe, predefined extension
    return safe_extension_map[user_extension]


def generate_secure_filename(original_filename):
    """Generate a secure, unique filename completely isolated from user input."""
    # Get a safe extension (breaks data flow from user input)
    safe_extension = get_safe_extension(original_filename)

    # Generate a completely new filename using only UUID and safe extension
    # This is completely independent of any user input
    unique_filename = f"{uuid.uuid4().hex}.{safe_extension}"

    # Final validation: ensure the generated filename is safe
    # This should never trigger since we control all components
    if ".." in unique_filename or "/" in unique_filename or "\\" in unique_filename:
        raise ValueError("Generated filename is unsafe")

    return unique_filename


@app.route("/posts/upload", methods=["POST"])
@token_required
def upload_file(current_user):
    """Upload a file with enhanced security validation."""
    if "file" not in request.files:
        return jsonify({"message": "No file part"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"message": "No selected file"}), 400

    # Validate file size (Flask's MAX_CONTENT_LENGTH handles this, but double-check)
    if hasattr(file, "content_length") and file.content_length > MAX_FILE_SIZE:
        return jsonify({"message": "File too large. Maximum size is 10MB"}), 413

    # Validate file type
    if not allowed_file(file.filename):
        return jsonify({"message": "File type not allowed"}), 400

    try:
        # Generate a secure filename completely isolated from user input
        secure_filename_generated = generate_secure_filename(file.filename)

        # Additional validation: ensure the secure filename is truly safe
        if not secure_filename_generated or not isinstance(
            secure_filename_generated, str
        ):
            raise ValueError("Invalid secure filename generated")

        # Validate the secure filename doesn't contain path characters
        if any(char in secure_filename_generated for char in ["/", "\\", "..", "\x00"]):
            raise ValueError("Generated filename contains invalid characters")

        # Create full path using only our controlled, safe filename
        # No user input is used in this path construction
        upload_folder = app.config["UPLOAD_FOLDER"]

        # Explicitly construct path with only safe, controlled components
        safe_filename = secure_filename_generated  # This is UUID + safe extension only
        file_path = os.path.join(upload_folder, safe_filename)

        # Additional security: ensure the file path is within the upload directory
        upload_dir = os.path.abspath(upload_folder)
        file_abs_path = os.path.abspath(file_path)
        if not file_abs_path.startswith(upload_dir + os.sep):
            app.logger.error(f"Path traversal attempt detected: {file_path}")
            return jsonify({"message": "Invalid file path"}), 400

        # Final check: ensure the filename in the path matches our secure filename
        actual_filename = os.path.basename(file_abs_path)
        if actual_filename != safe_filename:
            app.logger.error(
                f"Filename mismatch detected: expected {safe_filename}, got {actual_filename}"
            )
            return jsonify({"message": "Invalid file path"}), 400

        # Save the file to the validated path using our controlled filename
        file.save(file_path)

        # Return the URL path for the uploaded file using our safe filename
        file_url = f"/uploads/{safe_filename}"
        app.logger.info(
            f"File uploaded successfully by user {current_user.id}: {file_url}"
        )

        return (
            jsonify({"message": "File uploaded successfully", "filename": file_url}),
            200,
        )

    except ValueError as e:
        app.logger.warning(f"File upload validation error: {e}")
        # Only return safe, predefined error messages to avoid information exposure
        error_msg = "Invalid file or filename"
        if "File type not allowed" in str(e):
            error_msg = "File type not allowed"
        elif "Invalid filename" in str(e):
            error_msg = "Invalid filename"
        elif "File too large" in str(e):
            error_msg = "File too large"
        return jsonify({"message": error_msg}), 400
    except Exception as e:
        app.logger.error(f"File upload error: {e}")
        # Generic error message to prevent information disclosure
        return jsonify({"message": "Upload failed"}), 500


@app.route("/posts", methods=["POST"])
@token_required
def create_post(current_user):
    data = request.get_json()
    image_url = data.get("image_url")
    caption = data.get("caption")

    if not image_url or not caption:
        return jsonify({"message": "Image URL and caption are required"}), 400

    new_post = Post(user_id=current_user.id, image_url=image_url, caption=caption)
    session.add(new_post)
    session.commit()

    return (
        jsonify({"message": "Post created successfully", "post_id": new_post.id}),
        201,
    )


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    """Serve uploaded files with security validation."""
    # Validate filename to prevent directory traversal
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        app.logger.warning(f"Suspicious filename access attempt: {filename}")
        return jsonify({"message": "Invalid filename"}), 400

    # Ensure the requested file is within the upload directory
    try:
        upload_dir = os.path.abspath(app.config["UPLOAD_FOLDER"])
        requested_path = os.path.abspath(os.path.join(upload_dir, filename))

        if not requested_path.startswith(upload_dir):
            app.logger.warning(
                f"Path traversal attempt detected in file serving: {filename}"
            )
            return jsonify({"message": "Access denied"}), 403

        # Check if file exists
        if not os.path.isfile(requested_path):
            return jsonify({"message": "File not found"}), 404

        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    except Exception as e:
        app.logger.error(f"Error serving file {filename}: {e}")
        return jsonify({"message": "File access error"}), 500


@app.route("/posts/<int:post_id>/like", methods=["POST"])
@token_required
def toggle_like(current_user, post_id):
    """Toggle like on a post (like if not liked, unlike if already liked)"""
    # Check if post exists
    post = session.query(Post).filter_by(id=post_id).first()
    if not post:
        return jsonify({"message": "Post not found"}), 404

    # Check if user has access to this post (must be from a connection or own post)
    if post.user_id != current_user.id:
        # Check if post author is a connection
        connections = (
            session.query(Connection)
            .filter(
                or_(
                    (Connection.user_id1 == current_user.id)
                    & (Connection.user_id2 == post.user_id),
                    (Connection.user_id1 == post.user_id)
                    & (Connection.user_id2 == current_user.id),
                )
            )
            .first()
        )
        if not connections:
            return (
                jsonify(
                    {
                        "message": "Access denied. You can only like posts from connections."
                    }
                ),
                403,
            )

    # Check if user already liked this post
    existing_like = (
        session.query(Like).filter_by(user_id=current_user.id, post_id=post_id).first()
    )

    if existing_like:
        # Unlike the post
        session.delete(existing_like)
        session.commit()
        action = "unliked"
    else:
        # Like the post
        new_like = Like(user_id=current_user.id, post_id=post_id)
        session.add(new_like)
        session.commit()
        action = "liked"

        # Create notification for post owner (if not liking own post)
        if post.user_id != current_user.id:
            create_notification(
                user_id=post.user_id,
                actor_user_id=current_user.id,
                notification_type="post_liked",
                post_id=post_id,
            )

    # Get current like count
    like_count = session.query(Like).filter_by(post_id=post_id).count()

    return (
        jsonify(
            {
                "message": f"Post {action} successfully",
                "action": action,
                "like_count": like_count,
                "user_has_liked": action == "liked",
            }
        ),
        200,
    )


@app.route("/posts/<int:post_id>/likes", methods=["GET"])
@token_required
def get_post_likes(current_user, post_id):
    """Get like information for a post"""
    # Check if post exists
    post = session.query(Post).filter_by(id=post_id).first()
    if not post:
        return jsonify({"message": "Post not found"}), 404

    # Check if user has access to this post
    if post.user_id != current_user.id:
        connections = (
            session.query(Connection)
            .filter(
                or_(
                    (Connection.user_id1 == current_user.id)
                    & (Connection.user_id2 == post.user_id),
                    (Connection.user_id1 == post.user_id)
                    & (Connection.user_id2 == current_user.id),
                )
            )
            .first()
        )
        if not connections:
            return jsonify({"message": "Access denied"}), 403

    # Get like count
    like_count = session.query(Like).filter_by(post_id=post_id).count()

    # Check if current user liked this post
    user_has_liked = bool(
        session.query(Like).filter_by(user_id=current_user.id, post_id=post_id).first()
    )

    return (
        jsonify(
            {
                "post_id": post_id,
                "like_count": like_count,
                "user_has_liked": user_has_liked,
            }
        ),
        200,
    )


@app.route("/posts/<int:post_id>/comments", methods=["POST"])
@token_required
def add_comment(current_user, post_id):
    """Add a comment to a post"""
    data = request.get_json()
    content = data.get("content", "").strip()

    if not content:
        return jsonify({"message": "Comment content is required"}), 400

    if len(content) > 500:
        return jsonify({"message": "Comment must be 500 characters or less"}), 400

    # Check if post exists
    post = session.query(Post).filter_by(id=post_id).first()
    if not post:
        return jsonify({"message": "Post not found"}), 404

    # Check if user has access to this post
    if post.user_id != current_user.id:
        connections = (
            session.query(Connection)
            .filter(
                or_(
                    (Connection.user_id1 == current_user.id)
                    & (Connection.user_id2 == post.user_id),
                    (Connection.user_id1 == post.user_id)
                    & (Connection.user_id2 == current_user.id),
                )
            )
            .first()
        )
        if not connections:
            return (
                jsonify(
                    {
                        "message": "Access denied. You can only comment on posts from connections."
                    }
                ),
                403,
            )

    # Create new comment
    new_comment = Comment(user_id=current_user.id, post_id=post_id, content=content)
    session.add(new_comment)
    session.commit()

    # Create notification for post owner (if not commenting on own post)
    if post.user_id != current_user.id:
        create_notification(
            user_id=post.user_id,
            actor_user_id=current_user.id,
            notification_type="post_commented",
            post_id=post_id,
        )

    return (
        jsonify(
            {
                "message": "Comment added successfully",
                "comment": {
                    "id": new_comment.id,
                    "content": new_comment.content,
                    "created_at": new_comment.created_at.isoformat(),
                    "user_id": current_user.id,
                    "author_display_name": current_user.display_name,
                    "author_profile_picture_url": current_user.profile_picture_url,
                },
            }
        ),
        201,
    )


@app.route("/posts/<int:post_id>/comments", methods=["GET"])
@token_required
def get_post_comments(current_user, post_id):
    """Get comments for a post with pagination"""
    # Check if post exists
    post = session.query(Post).filter_by(id=post_id).first()
    if not post:
        return jsonify({"message": "Post not found"}), 404

    # Check if user has access to this post
    if post.user_id != current_user.id:
        connections = (
            session.query(Connection)
            .filter(
                or_(
                    (Connection.user_id1 == current_user.id)
                    & (Connection.user_id2 == post.user_id),
                    (Connection.user_id1 == post.user_id)
                    & (Connection.user_id2 == current_user.id),
                )
            )
            .first()
        )
        if not connections:
            return jsonify({"message": "Access denied"}), 403

    # Pagination parameters
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    # Limit per_page to prevent abuse
    if per_page > 50:
        per_page = 50

    # Get comments with pagination
    comments_query = (
        session.query(Comment)
        .filter_by(post_id=post_id)
        .order_by(Comment.created_at.asc())
    )

    total_comments = comments_query.count()
    comments = comments_query.offset((page - 1) * per_page).limit(per_page).all()

    comments_data = []
    for comment in comments:
        comment_user = session.query(User).filter_by(id=comment.user_id).first()
        comments_data.append(
            {
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
                "user_id": comment.user_id,
                "author_display_name": comment_user.display_name,
                "author_profile_picture_url": comment_user.profile_picture_url,
            }
        )

    return (
        jsonify(
            {
                "comments": comments_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_comments,
                    "pages": (total_comments + per_page - 1) // per_page,
                },
            }
        ),
        200,
    )


@app.route("/comments/<int:comment_id>", methods=["DELETE"])
@token_required
def delete_comment(current_user, comment_id):
    """Delete a comment (only by comment author)"""
    comment = session.query(Comment).filter_by(id=comment_id).first()
    if not comment:
        return jsonify({"message": "Comment not found"}), 404

    # Only comment author can delete their comment
    if comment.user_id != current_user.id:
        return (
            jsonify(
                {"message": "Access denied. You can only delete your own comments."}
            ),
            403,
        )

    session.delete(comment)
    session.commit()

    return jsonify({"message": "Comment deleted successfully"}), 200


@app.route("/notifications", methods=["GET"])
@token_required
def get_notifications(current_user):
    """Get unread notifications for the current user."""
    try:
        notifications = (
            session.query(Notification)
            .filter_by(user_id=current_user.id, is_read=False)
            .order_by(Notification.created_at.desc())
            .all()
        )

        notifications_data = []
        for notification in notifications:
            notifications_data.append(
                {
                    "id": notification.id,
                    "type": notification.type,
                    "message": notification.message,
                    "target_url": notification.target_url,
                    "created_at": notification.created_at.isoformat(),
                    "actor_user_id": notification.actor_user_id,
                    "post_id": notification.post_id,
                }
            )

        return jsonify(notifications_data), 200

    except Exception as e:
        app.logger.error(f"Error fetching notifications: {e}")
        return jsonify({"message": "Failed to fetch notifications"}), 500


@app.route("/notifications/<int:notification_id>/mark-read", methods=["POST"])
@token_required
def mark_notification_read(current_user, notification_id):
    """Mark a single notification as read."""
    try:
        notification = (
            session.query(Notification)
            .filter_by(id=notification_id, user_id=current_user.id)
            .first()
        )

        if not notification:
            return jsonify({"message": "Notification not found"}), 404

        notification.is_read = True
        session.commit()

        return jsonify({"message": "Notification marked as read"}), 200

    except Exception as e:
        session.rollback()
        app.logger.error(f"Error marking notification as read: {e}")
        return jsonify({"message": "Failed to mark notification as read"}), 500


@app.route("/notifications/mark-all-read", methods=["POST"])
@token_required
def mark_all_notifications_read(current_user):
    """Mark all notifications as read for the current user."""
    try:
        notifications = (
            session.query(Notification)
            .filter_by(user_id=current_user.id, is_read=False)
            .all()
        )

        for notification in notifications:
            notification.is_read = True

        session.commit()

        return (
            jsonify(
                {
                    "message": "All notifications marked as read",
                    "count": len(notifications),
                }
            ),
            200,
        )

    except Exception as e:
        session.rollback()
        app.logger.error(f"Error marking all notifications as read: {e}")
        return jsonify({"message": "Failed to mark all notifications as read"}), 500


if __name__ == "__main__":
    # Use environment variable for host, default to localhost for security
    import os

    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    app.run(host=host, port=port)
