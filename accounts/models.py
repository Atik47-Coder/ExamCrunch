from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.db.models.functions import Lower

from .validators import normalize_email,normalize_student_id

class UserManager(DjangoUserManager):
    @classmethod
    def normalize_email(cls,email):
        return normalize_email(email)

class User(AbstractUser):
    student_id=models.CharField(
        max_length=20,unique=True,null=True,blank=True,
        help_text='Students: exactly 8 digits, saved as text. Leave empty for administrator accounts.',
    )
    bio=models.TextField(blank=True)
    profile_image=models.ImageField(upload_to='profiles',blank=True)

    objects=UserManager()

    REQUIRED_FIELDS=['email']

    class Meta(AbstractUser.Meta):
        constraints=[
            models.UniqueConstraint(
                Lower('email'),
                condition=~models.Q(email=''),
                name='accounts_user_email_ci_unique',
                violation_error_message='An account with this email already exists.',
            ),
        ]

    def save(self,*args,**kwargs):
        self.email=normalize_email(self.email)
        self.student_id=normalize_student_id(self.student_id) or None
        super().save(*args,**kwargs)

    def display_name(self):
        return self.get_full_name() or self.username

    def __str__(self):
        return self.display_name()
