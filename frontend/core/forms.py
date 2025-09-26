"""Django forms for user registration, login, and content creation."""

from django import forms


class RegistrationForm(forms.Form):
    """Form for user registration with email and password."""

    email = forms.EmailField(label="Email", max_length=100)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)


class LoginForm(forms.Form):
    """Form for user authentication with email and password."""

    email = forms.EmailField(label="Email", max_length=100)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)


class ProfileEditForm(forms.Form):
    """Form for editing user profile information."""

    display_name = forms.CharField(label="Display Name", max_length=100, required=False)
    profile_picture_url = forms.URLField(label="Profile Picture URL", required=False)
    bio = forms.CharField(label="Bio", widget=forms.Textarea, required=False)


class CreatePostForm(forms.Form):
    """Form for creating new posts with image and caption."""

    image_url = forms.URLField(label="Image URL")
    caption = forms.CharField(label="Caption", widget=forms.Textarea, required=False)
