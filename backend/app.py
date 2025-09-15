import datetime
import logging
import sys
from functools import wraps

import jwt
from config import Config
from flask import Flask, jsonify, request
from models import Base, Connection, ConnectionRequest, Post, User
from sqlalchemy import create_engine, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

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


@app.route("/users/me", methods=["GET"])
@token_required
def get_current_user(current_user):
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
            jsonify(
                {
                    "message": "Connection request already exists or a similar issue occurred."
                }
            ),
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
        return jsonify({"message": "Pending connection request not found"}), 404

    # Create mutual connection
    user_id1 = min(connection_request.from_user_id, connection_request.to_user_id)
    user_id2 = max(connection_request.from_user_id, connection_request.to_user_id)

    new_connection = Connection(user_id1=user_id1, user_id2=user_id2)
    session.add(new_connection)

    # Update request status
    connection_request.status = "accepted"
    session.commit()

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
        posts_data.append(
            {
                "post_id": post.id,
                "caption": post.caption,
                "image_url": post.image_url,
                "created_at": post.created_at.isoformat(),
                "user_id": post.user_id,
                "author_display_name": current_user.display_name,  # Add this
                "author_profile_picture_url": current_user.profile_picture_url,  # Add this
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

        posts_data.append(
            {
                "post_id": post.id,
                "caption": post.caption,
                "image_url": post.image_url,
                "created_at": post.created_at.isoformat(),
                "user_id": post.user_id,
                "author_display_name": post_user.display_name,
                "author_profile_picture_url": post_user.profile_picture_url,
            }
        )
    return jsonify(posts_data), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
