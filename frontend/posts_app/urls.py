from django.urls import path

from . import views

urlpatterns = [
    path("users/<int:user_id>/posts/", views.post_list, name="post_list"),
]
