from django import forms

class RegistrationForm(forms.Form):
    email = forms.EmailField(label='Email', max_length=100)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

class LoginForm(forms.Form):
    email = forms.EmailField(label='Email', max_length=100)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

class ProfileEditForm(forms.Form):
    display_name = forms.CharField(label='Display Name', max_length=100, required=False)
    profile_picture_url = forms.URLField(label='Profile Picture URL', required=False)
    bio = forms.CharField(label='Bio', widget=forms.Textarea, required=False)

class CreatePostForm(forms.Form):
    image_url = forms.URLField(label='Image URL')
    caption = forms.CharField(label='Caption', widget=forms.Textarea, required=False)