import os

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string

from .storage import private_storage

class Course(models.Model):
    code=models.CharField(max_length=20)
    title=models.CharField(max_length=150)
    semester=models.CharField(max_length=30)
    section=models.CharField(max_length=10,blank=True)
    description=models.TextField(blank=True)
    invite_code=models.CharField(max_length=12,unique=True,blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                                 related_name='courses_created')
    is_archived=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together=('code','semester','section')
        ordering=['code','section']

    def make_new_invite_code(self):
        letters='ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        while True:
            code=get_random_string(8,allowed_chars=letters)
            if not Course.objects.filter(invite_code=code).exists():
                self.invite_code=code
                return code

    def save(self,*args,**kwargs):
        if not self.invite_code:
            self.make_new_invite_code()
        super().save(*args,**kwargs)

    def __str__(self):
        return f'{self.code} - {self.title}'

class Enrollment(models.Model):
    MEMBER='member'
    MODERATOR='moderator'
    ROLE_CHOICES=[(MEMBER,'Member'),(MODERATOR,'Moderator')]

    ACTIVE='active'
    LEFT='left'
    REMOVED='removed'
    STATUS_CHOICES=[(ACTIVE,'Active'),(LEFT,'Left'),(REMOVED,'Removed')]

    student=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                              related_name='enrollments')
    course=models.ForeignKey(Course,on_delete=models.CASCADE,related_name='enrollments')
    role=models.CharField(max_length=10,choices=ROLE_CHOICES,default=MEMBER)
    status=models.CharField(max_length=10,choices=STATUS_CHOICES,default=ACTIVE)
    joined_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together=('student','course')

    def is_moderator(self):
        return self.role==self.MODERATOR

    def __str__(self):
        return f'{self.student} in {self.course} ({self.role})'

class Topic(models.Model):
    course=models.ForeignKey(Course,on_delete=models.CASCADE,related_name='topics')
    title=models.CharField(max_length=150)
    description=models.TextField(blank=True)
    display_order=models.IntegerField(default=0)

    is_archived=models.BooleanField(default=False)

    class Meta:
        unique_together=('course','title')
        ordering=['display_order','title']

    def __str__(self):
        return f'{self.title} ({self.course.code})'

class Confidence(models.Model):
    NEED_HELP=1
    PRACTISING=2
    CAN_EXPLAIN=3
    LEVEL_CHOICES=[
        (NEED_HELP,'Need help'),
        (PRACTISING,'Practising'),
        (CAN_EXPLAIN,'Can explain'),
    ]

    student=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                              related_name='confidences')
    topic=models.ForeignKey(Topic,on_delete=models.CASCADE,related_name='confidences')
    level=models.IntegerField(choices=LEVEL_CHOICES)
    willing_to_help=models.BooleanField(default=False)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        unique_together=('student','topic')

    def __str__(self):
        return f'{self.student} - {self.topic.title}: {self.get_level_display()}'

class Resource(models.Model):
    topic=models.ForeignKey(Topic,on_delete=models.CASCADE,related_name='resources')
    uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                                  related_name='resources_uploaded')
    title=models.CharField(max_length=150)
    description=models.TextField(blank=True)

    file=models.FileField(upload_to='resources/%Y/%m/',storage=private_storage,blank=True)
    external_url=models.URLField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        ordering=['-created_at']

    def file_name(self):
        return os.path.basename(self.file.name) if self.file else ''

    def __str__(self):
        return self.title
