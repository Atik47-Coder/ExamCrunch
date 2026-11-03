from django.conf import settings
from django.db import models

from courses.models import Topic

class StudyGroup(models.Model):
    OPEN='open'
    CLOSED='closed'
    STATUS_CHOICES=[(OPEN,'Open'),(CLOSED,'Closed')]

    topic=models.ForeignKey(Topic,on_delete=models.CASCADE,related_name='study_groups')
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                                 related_name='groups_created')
    name=models.CharField(max_length=100)
    meeting_info=models.TextField(blank=True)
    max_members=models.IntegerField(default=6)
    status=models.CharField(max_length=6,choices=STATUS_CHOICES,default=OPEN)
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=['-created_at']

    def joined_memberships(self):
        return self.memberships.filter(status=GroupMembership.JOINED).select_related('student')

    def joined_count(self):
        return self.memberships.filter(status=GroupMembership.JOINED).count()

    def is_full(self):
        teacher=GroupHelperInvitation.objects.filter(group=self,status='accepted').first()
        learners=self.joined_memberships()
        if teacher:
            learners=learners.exclude(student_id=teacher.helper_id)
        return learners.count()>=self.max_members

    def is_open(self):
        return self.status==self.OPEN

    def __str__(self):
        return self.name

class GroupMembership(models.Model):
    JOINED='joined'
    LEFT='left'
    REMOVED='removed'
    STATUS_CHOICES=[(JOINED,'Joined'),(LEFT,'Left'),(REMOVED,'Removed')]

    group=models.ForeignKey(StudyGroup,on_delete=models.CASCADE,related_name='memberships')
    student=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                              related_name='group_memberships')
    status=models.CharField(max_length=8,choices=STATUS_CHOICES,default=JOINED)
    joined_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together=('group','student')

    def __str__(self):
        return f'{self.student} in {self.group} ({self.status})'

class GroupMessage(models.Model):
    group=models.ForeignKey(StudyGroup,on_delete=models.CASCADE,related_name='messages')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                             related_name='group_messages')
    body=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=['created_at']

    def __str__(self):
        return f'{self.author}: {self.body[:30]}'

class GroupHelperInvitation(models.Model):
    PENDING='pending'
    ACCEPTED='accepted'
    DECLINED='declined'
    WITHDRAWN='withdrawn'
    STATUS_CHOICES=[(PENDING,'Pending'),(ACCEPTED,'Accepted'),
                    (DECLINED,'Declined'),(WITHDRAWN,'Withdrawn')]
    group=models.OneToOneField(StudyGroup,on_delete=models.CASCADE,related_name='helper_invitation')
    helper=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                             related_name='group_invitations')
    invited_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                                 related_name='group_invitations_sent')
    status=models.CharField(max_length=10,choices=STATUS_CHOICES,default=PENDING)
    created_at=models.DateTimeField(auto_now_add=True)
