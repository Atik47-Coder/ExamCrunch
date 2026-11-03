from django.conf import settings
from django.core.validators import MinValueValidator,MaxValueValidator
from datetime import timedelta

from django.db import models
from django.utils import timezone

from courses.models import Topic,Confidence,Enrollment

ANONYMOUS_NAME='Anonymous student'

class HelpRequest(models.Model):
    OPEN='open'
    IN_PROGRESS='in_progress'
    RESOLVED='resolved'
    CANCELLED='cancelled'
    STATUS_CHOICES=[
        (OPEN,'Open'),
        (IN_PROGRESS,'In progress'),
        (RESOLVED,'Resolved'),
        (CANCELLED,'Cancelled'),
    ]

    requester=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                                related_name='requests_made')
    assigned_helper=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,
                                      null=True,blank=True,related_name='requests_helping')
    topic=models.ForeignKey(Topic,on_delete=models.CASCADE,related_name='help_requests')

    title=models.CharField(max_length=150)
    description=models.TextField()
    status=models.CharField(max_length=12,choices=STATUS_CHOICES,default=OPEN)
    is_anonymous=models.BooleanField(default=False)

    confidence_before=models.IntegerField(choices=Confidence.LEVEL_CHOICES)
    confidence_after=models.IntegerField(choices=Confidence.LEVEL_CHOICES,null=True,blank=True)

    created_at=models.DateTimeField(auto_now_add=True)
    assigned_at=models.DateTimeField(null=True,blank=True)
    resolved_at=models.DateTimeField(null=True,blank=True)

    class Meta:
        ordering=['-created_at']

    @property
    def course(self):
        return self.topic.course

    def is_active(self):
        return self.status in (self.OPEN,self.IN_PROGRESS)

    def identity_visible_to(self,viewer):
        if not self.is_anonymous:
            return True
        if viewer==self.requester:
            return True

        return Enrollment.objects.filter(
            student=viewer,course=self.topic.course_id,
            role=Enrollment.MODERATOR,status=Enrollment.ACTIVE).exists()

    def display_name_for(self,viewer):
        if self.identity_visible_to(viewer):
            return self.requester.display_name()
        return ANONYMOUS_NAME

    def __str__(self):
        return self.title

class HelpInvitation(models.Model):
    PENDING='pending'
    ACCEPTED='accepted'
    DECLINED='declined'
    WITHDRAWN='withdrawn'
    EXPIRED='expired'
    STATUS_CHOICES=[
        (PENDING,'Pending'),
        (ACCEPTED,'Accepted'),
        (DECLINED,'Declined'),
        (WITHDRAWN,'Withdrawn'),
        (EXPIRED,'Expired'),
    ]

    request=models.ForeignKey(HelpRequest,on_delete=models.CASCADE,related_name='invitations')
    helper=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                             related_name='help_invitations')
    status=models.CharField(max_length=10,choices=STATUS_CHOICES,default=PENDING)
    created_at=models.DateTimeField(auto_now_add=True)
    responded_at=models.DateTimeField(null=True,blank=True)

    class Meta:
        unique_together=('request','helper')
        ordering=['created_at']

    def expires_at(self):
        return self.created_at + timedelta(hours=settings.INVITATION_EXPIRY_HOURS)

    def __str__(self):
        return f'{self.helper} -> {self.request} ({self.status})'

class Response(models.Model):
    request=models.ForeignKey(HelpRequest,on_delete=models.CASCADE,related_name='responses')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                             related_name='responses')
    body=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        ordering=['created_at']

    def author_name_for(self,viewer):
        if self.author_id==self.request.requester_id:
            return self.request.display_name_for(viewer)
        return self.author.display_name()

    def __str__(self):
        return f'Reply by {self.author} on {self.request}'

class Feedback(models.Model):
    request=models.OneToOneField(HelpRequest,on_delete=models.CASCADE,related_name='feedback')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                             related_name='feedback_given')
    helper=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                             related_name='feedback_received')
    helpfulness_rating=models.IntegerField(
        validators=[MinValueValidator(1),MaxValueValidator(5)])
    comment=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.helpfulness_rating}/5 for {self.helper}'

def expire_old_invitations():
    cutoff=timezone.now() - timedelta(hours=settings.INVITATION_EXPIRY_HOURS)
    HelpInvitation.objects.filter(status=HelpInvitation.PENDING,created_at__lt=cutoff).update(
        status=HelpInvitation.EXPIRED,responded_at=timezone.now())
