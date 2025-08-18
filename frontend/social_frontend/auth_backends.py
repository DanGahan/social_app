import requests
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class FlaskUserBackend(ModelBackend):
    def authenticate(self, request, apple_id=None, email=None, **kwargs):
        if apple_id and email:
            # Call your Flask backend to manage the user
            flask_api_url = "http://social_backend:5000/users/manage"
            try:
                response = requests.post(flask_api_url, json={'apple_id': apple_id, 'email': email})
                response.raise_for_status()  # Raise an exception for HTTP errors
                user_data = response.json()
                flask_user_id = user_data.get('user_id')

                if flask_user_id:
                    # Try to get the Django user. If not exists, create it.
                    # We'll use the flask_user_id as the username for simplicity
                    # or you might map it to a custom user model field.
                    try:
                        user = User.objects.get(username=flask_user_id)
                    except User.DoesNotExist:
                        user = User.objects.create_user(username=flask_user_id, email=email)
                    return user
            except requests.exceptions.RequestException as e:
                print(f"Error communicating with Flask backend: {e}")
                return None
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
