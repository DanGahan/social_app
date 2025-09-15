from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("", views.home_view, name="home"),
    path(
        "connections/send/",
        views.send_connection_request_view,
        name="send_connection_request",
    ),
    path(
        "connections/accept/",
        views.accept_connection_request_view,
        name="accept_connection_request",
    ),
    path(
        "connections/deny/",
        views.deny_connection_request_view,
        name="deny_connection_request",
    ),
    path("api/users/search/", views.search_users_view, name="search_users"),
    path(
        "api/users/<int:user_id>/profile_and_posts/",
        views.get_user_profile_and_posts,
        name="get_user_profile_and_posts",
    ),
    path(
        "api/connections/request",
        views.api_request_connection,
        name="api_request_connection",
    ),
]
