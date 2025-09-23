"""
URL configuration for social_frontend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from core.views import api_create_post, api_upload_image, serve_uploaded_image
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("posts/", include("posts_app.urls")),
    path("", include("core.urls")),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # API proxy routes
    path("api/posts/upload-image", api_upload_image, name="api_upload_image"),
    path("api/posts", api_create_post, name="api_create_post"),
    # Image serving route
    path("uploads/<str:filename>", serve_uploaded_image, name="serve_uploaded_image"),
]
