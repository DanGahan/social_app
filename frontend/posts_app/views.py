import requests
from django.conf import settings
from django.contrib import messages  # Import messages
from django.shortcuts import redirect, render


def post_list(request, user_id):
    # In a real application, you'd get the user_id from the authenticated user
    # For now, we'll use a hardcoded user_id or one passed in the URL

    backend_url = f"http://social_backend:5000/users/{user_id}/posts"
    try:
        response = requests.get(backend_url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        posts = response.json()
    except requests.exceptions.RequestException as e:
        messages.error(request, f"Error fetching posts: {e}")
        posts = []

    context = {"user_id": user_id, "posts": posts}
    return render(request, "posts_app/post_list.html", context)


def add_post(request):
    if request.method == "POST":
        image_url = request.POST.get("image_url")
        caption = request.POST.get("caption")
        user_id = request.session.get("user_id")  # Assuming user_id is in session
        token = request.session.get("jwt_token")  # Assuming JWT token is in session

        if not user_id or not token:
            messages.error(request, "You must be logged in to add a post.")
            return redirect("login")  # Redirect to login if not authenticated

        if not image_url:
            messages.error(request, "Image URL is required.")
            return render(request, "posts_app/add_post.html", {"caption": caption})

        if not caption:
            messages.error(request, "Caption is required.")
            return render(request, "posts_app/add_post.html", {"image_url": image_url})

        headers = {"x-access-token": token}
        payload = {"image_url": image_url, "caption": caption}
        backend_url = f"http://social_backend:5000/posts"
        try:
            response = requests.post(backend_url, json=payload, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
            messages.success(request, "Post created successfully!")
            return redirect("post_list", user_id=user_id)  # Redirect to user's post list
        except requests.exceptions.RequestException as e:
            messages.error(request, f"Error creating post: {e}")
            return render(
                request, "posts_app/add_post.html", {"image_url": image_url, "caption": caption}
            )
    return render(request, "posts_app/add_post.html")
