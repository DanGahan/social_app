import requests
from django.conf import settings
from django.shortcuts import redirect, render


def post_list(request, user_id):
    # In a real application, you'd get the user_id from the authenticated user
    # For now, we'll use a hardcoded user_id or one passed in the URL

    backend_url = f"http://social_backend:5000/users/{user_id}/posts"
    response = requests.get(backend_url)

    posts = []
    if response.status_code == 200:
        posts = response.json()
    else:
        # Handle error, e.g., log it or show a message to the user
        print(f"Error fetching posts: {response.status_code} - {response.text}")

    context = {"user_id": user_id, "posts": posts}
    return render(request, "posts_app/post_list.html", context)


def add_post(request):
    if request.method == "POST":
        image_url = request.POST.get("image_url")
        caption = request.POST.get("caption")
        user_id = request.session.get("user_id")  # Assuming user_id is in session
        token = request.session.get("jwt_token")  # Assuming JWT token is in session

        if not user_id or not token:
            return redirect("login")  # Redirect to login if not authenticated

        headers = {"x-access-token": token}
        payload = {"image_url": image_url, "caption": caption}
        backend_url = f"http://social_backend:5000/posts"
        response = requests.post(backend_url, json=payload, headers=headers)

        if response.status_code == 201:
            return redirect("post_list", user_id=user_id)  # Redirect to user's post list
        else:
            # Handle error, e.g., show error message on the form
            print(f"Error creating post: {response.status_code} - {response.text}")
            return render(request, "posts_app/add_post.html", {"error": response.json().get("message")})
    return render(request, "posts_app/add_post.html")
