import requests
from django.shortcuts import render


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
