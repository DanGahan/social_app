import json
import logging
from datetime import datetime

import requests
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

from django.http import JsonResponse  # New import
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import CreatePostForm, LoginForm, ProfileEditForm, RegistrationForm

# Define the Flask backend URL
FLASK_BACKEND_URL = (
    "http://social_backend:5000"  # Use the service name from docker-compose
)


def register_view(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            try:
                response = requests.post(
                    f"{FLASK_BACKEND_URL}/auth/register",
                    json={"email": email, "password": password},
                )
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                messages.success(request, "Registration successful! Please log in.")
                return redirect(reverse("login"))
            except requests.exceptions.RequestException as e:
                messages.error(request, f"Registration failed: {e}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()
    return render(request, "core/registration.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            try:
                response = requests.post(
                    f"{FLASK_BACKEND_URL}/auth/login",
                    json={"email": email, "password": password},
                )
                response.raise_for_status()

                data = response.json()
                token = data.get("token")

                if token:
                    request.session["jwt_token"] = token
                    # messages.success(request, 'Login successful!') # Removed this line
                    return redirect(reverse("home"))
                else:
                    messages.error(
                        request, "Login failed: Invalid response from server."
                    )
            except requests.exceptions.RequestException as e:
                messages.error(request, f"Login failed: {e}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LoginForm()
    return render(request, "core/login.html", {"form": form})


def home_view(request):
    jwt_token = request.session.get("jwt_token")

    if not jwt_token:
        messages.warning(request, "Please log in to view this page.")
        return redirect(reverse("login"))

    user_id = None
    my_posts = []
    connections = []
    pending_requests = []
    sent_requests = []
    connections_posts = []
    profile_picture_url = None
    display_name = None
    profile_data = {}
    profile_form = ProfileEditForm()  # Initialize for GET
    create_post_form = CreatePostForm()  # Initialize for GET

    # Fetch user_id and profile info from backend /users/me endpoint
    try:
        headers = {"x-access-token": jwt_token}
        user_response = requests.get(f"{FLASK_BACKEND_URL}/users/me", headers=headers)
        user_response.raise_for_status()
        user_data = user_response.json()
        user_id = user_data.get("user_id")
        profile_picture_url = user_data.get("profile_picture_url")
        display_name = user_data.get("display_name")
        request.session["user_id"] = user_id
        request.session["profile_picture_url"] = user_data.get("profile_picture_url")
        request.session["display_name"] = user_data.get("display_name")

        # Fetch profile data for the profile tab
        profile_response = requests.get(
            f"{FLASK_BACKEND_URL}/users/{user_id}/profile", headers=headers
        )
        profile_response.raise_for_status()
        profile_data = profile_response.json()
        profile_form = ProfileEditForm(
            initial={
                "display_name": profile_data.get("display_name", ""),
                "profile_picture_url": profile_data.get("profile_picture_url", ""),
                "bio": profile_data.get("bio", ""),
            }
        )

    except requests.exceptions.RequestException as e:
        messages.error(request, f"Session expired or invalid. Please log in again: {e}")
        return redirect(reverse("login"))

    # Handle POST requests for profile update and create post
    if request.method == "POST":
        if (
            "update_profile" in request.POST
        ):  # Check if profile update button was clicked
            profile_form = ProfileEditForm(request.POST)
            if profile_form.is_valid():
                display_name = profile_form.cleaned_data["display_name"]
                profile_picture_url = profile_form.cleaned_data["profile_picture_url"]
                bio = profile_form.cleaned_data["bio"]

                try:
                    headers = {
                        "x-access-token": jwt_token,
                        "Content-Type": "application/json",
                    }
                    update_data = {}
                    if display_name is not None:
                        update_data["display_name"] = display_name
                    if profile_picture_url is not None:
                        update_data["profile_picture_url"] = profile_picture_url
                    if bio is not None:
                        update_data["bio"] = bio

                    response = requests.put(
                        f"{FLASK_BACKEND_URL}/users/{user_id}/profile",
                        json=update_data,
                        headers=headers,
                    )
                    response.raise_for_status()
                    messages.success(request, "Profile updated successfully!")
                    # Re-fetch user data to update session with new profile_picture_url and display_name
                    user_response = requests.get(
                        f"{FLASK_BACKEND_URL}/users/me", headers=headers
                    )
                    user_response.raise_for_status()
                    user_data = user_response.json()
                    request.session["profile_picture_url"] = user_data.get(
                        "profile_picture_url"
                    )
                    request.session["display_name"] = user_data.get("display_name")
                    return redirect(
                        reverse("home")
                    )  # Redirect to home to show updated info
                except requests.exceptions.RequestException as e:
                    messages.error(request, f"Failed to update profile: {e}")
            else:
                messages.error(
                    request,
                    "Please correct the errors below for profile update.",
                )
        elif "create_post" in request.POST:  # Check if create post button was clicked
            create_post_form = CreatePostForm(request.POST)
            if create_post_form.is_valid():
                image_url = create_post_form.cleaned_data["image_url"]
                caption = create_post_form.cleaned_data["caption"]

                try:
                    headers = {
                        "x-access-token": jwt_token,
                        "Content-Type": "application/json",
                    }
                    post_data = {"image_url": image_url, "caption": caption}
                    response = requests.post(
                        f"{FLASK_BACKEND_URL}/posts",
                        json=post_data,
                        headers=headers,
                    )
                    response.raise_for_status()
                    messages.success(request, "Post created successfully!")
                    return redirect(
                        reverse("home")
                    )  # Redirect to home to show new post
                except requests.exceptions.RequestException as e:
                    messages.error(request, f"Failed to create post: {e}")
            else:
                messages.error(
                    request,
                    "Please correct the errors below for post creation.",
                )
        # If neither form was submitted, or if there are other POST requests,
        # re-initialize forms with data to display errors if any
        # For profile form, re-populate with current profile data if it was not a profile update POST
        if "update_profile" not in request.POST:
            profile_form = ProfileEditForm(
                initial={
                    "display_name": profile_data.get("display_name", ""),
                    "profile_picture_url": profile_data.get("profile_picture_url", ""),
                    "bio": profile_data.get("bio", ""),
                }
            )
        # For create post form, re-initialize if it was not a create post POST
        if "create_post" not in request.POST:
            create_post_form = CreatePostForm()

    # Fetch My Posts
    if user_id:
        try:
            headers = {"x-access-token": jwt_token}
            posts_response = requests.get(
                f"{FLASK_BACKEND_URL}/users/{user_id}/posts", headers=headers
            )
            posts_response.raise_for_status()
            my_posts = posts_response.json()
            for post in my_posts:
                if isinstance(post.get("created_at"), str):
                    post["created_at"] = datetime.fromisoformat(post["created_at"])
            my_posts.sort(
                key=lambda x: x["created_at"], reverse=True
            )  # Sort by created_at in reverse chronological order
        except requests.exceptions.RequestException as e:
            messages.error(request, f"Could not fetch my posts: {e}")

        # Fetch Connections
        try:
            headers = {"x-access-token": jwt_token}
            connections_response = requests.get(
                f"{FLASK_BACKEND_URL}/users/{user_id}/connections",
                headers=headers,
            )
            connections_response.raise_for_status()
            connections = connections_response.json()
        except requests.exceptions.RequestException as e:
            messages.error(request, f"Could not fetch connections: {e}")

        # Fetch Pending Requests
        try:
            headers = {"x-access-token": jwt_token}
            pending_response = requests.get(
                f"{FLASK_BACKEND_URL}/users/{user_id}/pending_requests",
                headers=headers,
            )
            pending_response.raise_for_status()
            pending_requests_raw = pending_response.json()
            # Process pending_requests to flatten user data for template
            pending_requests = []
            for req in pending_requests_raw:
                processed_req = req.copy()
                if "from_user" in req and req["from_user"]:
                    processed_req["from_user_display_name"] = req["from_user"].get(
                        "display_name", "N/A"
                    )
                    processed_req["from_user_profile_picture_url"] = req[
                        "from_user"
                    ].get(
                        "profile_picture_url",
                        "/static/default_profile_pic.png",
                    )
                pending_requests.append(processed_req)
        except requests.exceptions.RequestException as e:
            messages.error(request, f"Could not fetch pending requests: {e}")

        # Fetch Sent Requests
        try:
            headers = {"x-access-token": jwt_token}
            sent_response = requests.get(
                f"{FLASK_BACKEND_URL}/users/{user_id}/sent_requests",
                headers=headers,
            )
            sent_response.raise_for_status()
            sent_requests_raw = sent_response.json()
            # Process sent_requests to flatten user data for template
            sent_requests = []
            for req in sent_requests_raw:
                processed_req = req.copy()
                if "to_user" in req and req["to_user"]:
                    processed_req["to_user_display_name"] = req["to_user"].get(
                        "display_name", "N/A"
                    )
                    processed_req["to_user_profile_picture_url"] = req["to_user"].get(
                        "profile_picture_url",
                        "/static/default_profile_pic.png",
                    )
                sent_requests.append(processed_req)
        except requests.exceptions.RequestException as e:
            messages.error(request, f"Could not fetch sent requests: {e}")

        # Fetch Connections' Posts
        try:
            headers = {"x-access-token": jwt_token}
            connections_posts_response = requests.get(
                f"{FLASK_BACKEND_URL}/users/{user_id}/connections/posts",
                headers=headers,
            )
            connections_posts_response.raise_for_status()
            connections_posts = connections_posts_response.json()
            for post in connections_posts:
                if isinstance(post.get("created_at"), str):
                    post["created_at"] = datetime.fromisoformat(post["created_at"])
        except requests.exceptions.RequestException as e:
            messages.error(request, f"Could not fetch connections' posts: {e}")

    return render(
        request,
        "core/home.html",
        {
            "jwt_token": jwt_token,
            "user_id": user_id,
            "my_posts": my_posts,
            "connections": connections,
            "pending_requests": pending_requests,
            "sent_requests": sent_requests,
            "connections_posts": connections_posts,
            "profile_picture_url": profile_picture_url,
            "display_name": display_name,
            "profile_data": profile_data,  # Pass profile_data to template
            "profile_form": profile_form,  # Corrected: Pass profile_form as 'profile_form'
            "create_post_form": create_post_form,  # Pass create_post_form to template
            "flask_backend_url": FLASK_BACKEND_URL,
        },
    )


def send_connection_request_view(request):
    jwt_token = request.session.get("jwt_token")
    user_id = request.session.get("user_id")

    if not jwt_token or not user_id:
        messages.warning(request, "Please log in to send connection requests.")
        return redirect(reverse("login"))

    if request.method == "POST":
        to_user_id = request.POST.get("to_user_id")
        if to_user_id:
            try:
                headers = {"x-access-token": jwt_token}
                response = requests.post(
                    f"{FLASK_BACKEND_URL}/connections/request",
                    json={"to_user_id": int(to_user_id)},
                    headers=headers,
                )
                response.raise_for_status()
                messages.success(request, "Connection request sent!")
            except requests.exceptions.RequestException as e:
                messages.error(request, f"Failed to send request: {e}")
        else:
            messages.error(request, "Please provide a user ID to connect to.")
        return redirect(reverse("home"))  # Redirect back to home after sending request
    return redirect(reverse("home"))


def accept_connection_request_view(request):
    jwt_token = request.session.get("jwt_token")
    user_id = request.session.get("user_id")

    if not jwt_token or not user_id:
        messages.warning(request, "Please log in to accept connection requests.")
        return redirect(reverse("login"))

    if request.method == "POST":
        request_id = request.POST.get("request_id")
        if request_id:
            try:
                headers = {"x-access-token": jwt_token}
                response = requests.post(
                    f"{FLASK_BACKEND_URL}/connections/accept",
                    json={"request_id": int(request_id)},
                    headers=headers,
                )
                response.raise_for_status()
                messages.success(request, "Connection request accepted!")
            except requests.exceptions.RequestException as e:
                messages.error(request, f"Failed to accept request: {e}")
        else:
            messages.error(request, "Invalid request.")
    return redirect(reverse("home"))  # Always redirect back to home


def deny_connection_request_view(request):
    jwt_token = request.session.get("jwt_token")
    user_id = request.session.get("user_id")

    if not jwt_token or not user_id:
        messages.warning(request, "Please log in to deny connection requests.")
        return redirect(reverse("login"))

    if request.method == "POST":
        request_id = request.POST.get("request_id")
        if request_id:
            try:
                headers = {"x-access-token": jwt_token}
                response = requests.post(
                    f"{FLASK_BACKEND_URL}/connections/deny",
                    json={"request_id": int(request_id)},
                    headers=headers,
                )
                response.raise_for_status()
                messages.success(request, "Connection request denied!")
            except requests.exceptions.RequestException as e:
                messages.error(request, f"Failed to deny request: {e}")
        else:
            messages.error(request, "Invalid request.")
    return redirect(reverse("home"))  # Always redirect back to home


def search_users_view(request):
    jwt_token = request.session.get("jwt_token")
    if not jwt_token:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    query = request.GET.get("query", "")
    if not query:
        return JsonResponse({"users": []})

    try:
        headers = {"x-access-token": jwt_token}
        response = requests.get(
            f"{FLASK_BACKEND_URL}/users/search?query={query}", headers=headers
        )
        response.raise_for_status()
        users = response.json()
        return JsonResponse({"users": users})
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": "Failed to search users."}, status=500)


def get_user_profile_and_posts(request, user_id):
    jwt_token = request.session.get("jwt_token")
    if not jwt_token:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        headers = {"x-access-token": jwt_token}
        # Fetch user profile
        profile_response = requests.get(
            f"{FLASK_BACKEND_URL}/users/{user_id}/profile", headers=headers
        )
        profile_response.raise_for_status()  # This will raise an exception for 4xx/5xx responses
        try:
            profile_data = profile_response.json()
        except ValueError:
            return JsonResponse(
                {"error": "Profile data is not valid JSON from Flask backend."},
                status=500,
            )

        # Fetch user posts
        posts_response = requests.get(
            f"{FLASK_BACKEND_URL}/users/{user_id}/posts", headers=headers
        )
        posts_response.raise_for_status()  # This will raise an exception for 4xx/5xx responses
        try:
            user_posts = posts_response.json()
        except ValueError:
            return JsonResponse(
                {"error": "User posts data is not valid JSON from Flask backend."},
                status=500,
            )

        # Convert created_at to string for JSON serialization
        for post in user_posts:
            if isinstance(post.get("created_at"), datetime):
                post["created_at"] = post["created_at"].isoformat()

        return JsonResponse({"profile": profile_data, "posts": user_posts})
    except requests.exceptions.RequestException as e:
        logger.error(f"Request to Flask backend failed: {e}")
        return JsonResponse({"error": "Failed to retrieve user data."}, status=500)
    except Exception as e:  # Catch any other unexpected errors
        logger.error(f"An unexpected error occurred in Django view: {e}")
        return JsonResponse(
            {"error": "An unexpected error occurred."},
            status=500,
        )


def api_request_connection(request):
    jwt_token = request.session.get("jwt_token")
    user_id = request.session.get("user_id")

    if not jwt_token or not user_id:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if request.method == "POST":
        data = json.loads(request.body)
        to_user_id = data.get("to_user_id")
        if to_user_id:
            try:
                headers = {"x-access-token": jwt_token}
                response = requests.post(
                    f"{FLASK_BACKEND_URL}/connections/request",
                    json={"to_user_id": int(to_user_id)},
                    headers=headers,
                )
                response.raise_for_status()
                return JsonResponse(response.json())
            except requests.exceptions.RequestException as e:
                return JsonResponse({"error": "Failed to send request."}, status=500)
        else:
            return JsonResponse(
                {"error": "Please provide a user ID to connect to."},
                status=400,
            )


@csrf_exempt
def api_upload_image(request):
    """Proxy for image upload to Flask backend"""
    jwt_token = request.session.get("jwt_token")

    if not jwt_token:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if request.method == "POST":
        try:
            headers = {"x-access-token": jwt_token}

            # Check if file is present
            if "file" not in request.FILES:
                return JsonResponse({"error": "No file provided"}, status=400)

            uploaded_file = request.FILES["file"]
            if not uploaded_file.name:
                return JsonResponse({"error": "No file selected"}, status=400)

            # Forward the file to the backend
            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.read(),
                    uploaded_file.content_type,
                )
            }

            print(
                f"Uploading file: {uploaded_file.name}, size: {uploaded_file.size}, type: {uploaded_file.content_type}"
            )

            response = requests.post(
                f"{FLASK_BACKEND_URL}/posts/upload",
                headers=headers,
                files=files,
            )

            # Return the backend response
            if response.ok:
                return JsonResponse(response.json())
            else:
                return JsonResponse(
                    {"error": response.text or "Upload failed"},
                    status=response.status_code,
                )

        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": "Failed to upload image."}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def api_create_post(request):
    """Proxy for post creation to Flask backend"""
    jwt_token = request.session.get("jwt_token")

    if not jwt_token:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if request.method == "POST":
        try:
            headers = {"x-access-token": jwt_token, "Content-Type": "application/json"}

            # Forward the JSON data to the backend
            data = json.loads(request.body)

            response = requests.post(
                f"{FLASK_BACKEND_URL}/posts",
                headers=headers,
                json=data,
            )

            # Return the backend response
            if response.ok:
                return JsonResponse(response.json())
            else:
                try:
                    error_data = response.json()
                    return JsonResponse(error_data, status=response.status_code)
                except:
                    return JsonResponse(
                        {"error": response.text or "Post creation failed"},
                        status=response.status_code,
                    )

        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": "Failed to create post."}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data."}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)


def serve_uploaded_image(request, filename):
    """Proxy to serve uploaded images from Flask backend"""
    try:
        response = requests.get(f"{FLASK_BACKEND_URL}/uploads/{filename}")

        if response.ok:
            from django.http import HttpResponse

            return HttpResponse(
                response.content,
                content_type=response.headers.get("content-type", "image/jpeg"),
            )
        else:
            from django.http import Http404

            raise Http404("Image not found")

    except requests.exceptions.RequestException:
        from django.http import Http404

        raise Http404("Image not found")
