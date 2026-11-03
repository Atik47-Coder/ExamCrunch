from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .validators import normalize_email

class EmailBackend(ModelBackend):
    def authenticate(self,request,email=None,password=None,**kwargs):
        if email is None or password is None:
            return None
        email=normalize_email(email)
        if not email:
            return None

        User=get_user_model()
        try:
            user=User._default_manager.get(email__iexact=email)
        except (User.DoesNotExist,User.MultipleObjectsReturned):
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
