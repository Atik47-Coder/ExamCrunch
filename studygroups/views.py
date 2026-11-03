from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Avg,Count
from django.http import Http404
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from accounts.models import User
from courses.models import Confidence,Enrollment,Topic
from courses.views import get_topic_and_membership,get_course_and_membership
from helpdesk.models import Feedback
from .form import GroupInfoForm,GroupMessageForm
from .models import StudyGroup,GroupMembership,GroupMessage,GroupHelperInvitation

@login_required
def start_group(request,topic_id):
    topic,course,membership=get_topic_and_membership(request.user,topic_id)
    if request.method!='POST':
        return redirect('topic_detail',topic_id=topic.id)

    prompt=group_prompt(request.user,topic)
    if prompt is None:
        messages.error(request,'A study group needs you to rate this topic "Need help" '
                                'and enough classmates who need help too.')
        return redirect('topic_detail',topic_id=topic.id)
    if prompt['group'] is not None:
        messages.info(request,'A study group for this topic already exists. You can join it.')
        return redirect('topic_detail',topic_id=topic.id)

    group=StudyGroup.objects.create(topic=topic,created_by=request.user,
                                    name=f'{topic.title} study group')
    GroupMembership.objects.create(group=group,student=request.user)
    messages.success(request,'Study group started! Add a place and time so classmates know when to meet.')
    return redirect('group_detail',group_id=group.id)

@login_required
def join_group(request,group_id):
    group=get_object_or_404(StudyGroup.objects.select_related('topic__course'),pk=group_id)
    topic,course,membership=get_topic_and_membership(request.user,group.topic_id)
    if request.method!='POST':
        return redirect('topic_detail',topic_id=topic.id)

    prompt=group_prompt(request.user,topic)
    if prompt is None or prompt['group'] is None or prompt['group'].id!=group.id:
        messages.error(request,'You cannot join this group.')
        return redirect('topic_detail',topic_id=topic.id)
    if prompt['is_member']:
        return redirect('group_detail',group_id=group.id)
    if not prompt['can_join']:
        messages.error(request,'Sorry, this group is full.' if prompt.get('is_full')
                       else 'You cannot join this group.')
        return redirect('topic_detail',topic_id=topic.id)

    member,created=GroupMembership.objects.get_or_create(group=group,student=request.user)
    if not created:
        member.status=GroupMembership.JOINED
        member.save()
    messages.success(request,'You joined the study group. Only members can see each other.')
    return redirect('group_detail',group_id=group.id)

@login_required
def leave_group(request,group_id):
    group,member=get_group_for_member(request.user,group_id)
    if request.method=='POST':
        GroupHelperInvitation.objects.filter(group=group,helper=request.user,status='accepted').update(status='withdrawn')
        member.status=GroupMembership.LEFT
        member.save()
        if group.joined_count()==0:
            group.status=StudyGroup.CLOSED
            group.save()
            GroupHelperInvitation.objects.filter(group=group,status='pending').update(status='withdrawn')
        messages.info(request,'You left the study group.')
    return redirect('my_groups')

@login_required
def close_group(request,group_id):
    group,member=get_group_for_member(request.user,group_id)
    if request.method=='POST' and group.is_open():
        group.status=StudyGroup.CLOSED
        group.save()
        GroupHelperInvitation.objects.filter(group=group,status='pending').update(status='withdrawn')
        messages.info(request,'The study group is closed. Well done!')
    return redirect('group_detail',group_id=group.id)

@login_required
def group_detail(request,group_id):
    group,member=get_group_for_member(request.user,group_id)

    if request.method=='POST':
        if not group.is_open():
            messages.error(request,'This group is closed.')
            return redirect('group_detail',group_id=group.id)
        form=GroupMessageForm(request.POST)
        if form.is_valid():
            message=form.save(commit=False)
            message.group=group
            message.author=request.user
            message.save()
            return redirect('group_detail',group_id=group.id)
    else:
        form=GroupMessageForm()

    return render(request,'studygroups/group_detail.html',{
        'group':group,
        'topic':group.topic,
        'course':group.topic.course,
        'members':group.joined_memberships(),
        'group_messages':group.messages.select_related('author'),
        'form':form,
        'helper_invitation':GroupHelperInvitation.objects.filter(group=group).select_related('helper').first(),
        'helper_candidates':[row for row in helper_candidates(group) if row['user'].pk!=request.user.pk] if group.is_open() and not group.topic.is_archived else [],
    })

@login_required
def edit_group(request,group_id):
    group,member=get_group_for_member(request.user,group_id)
    if request.method=='POST':
        form=GroupInfoForm(request.POST,instance=group)
        if form.is_valid():
            form.save()
            messages.success(request,'Group details saved.')
            return redirect('group_detail',group_id=group.id)
    else:
        form=GroupInfoForm(instance=group)
    return render(request,'studygroups/group_form.html',{
        'form':form,'group':group,
    })

@login_required
def delete_group_message(request,message_id):
    message=get_object_or_404(GroupMessage.objects.select_related('group'),pk=message_id)
    group,member=get_group_for_member(request.user,message.group_id)
    if message.author_id!=request.user.id:
        raise PermissionDenied('You can only delete your own messages.')
    if request.method=='POST':
        message.delete()
    return redirect('group_detail',group_id=group.id)

@login_required
def my_groups(request):
    memberships=GroupMembership.objects.filter(
        student=request.user,status=GroupMembership.JOINED,
        group__topic__course__is_archived=False,
    ).select_related('group__topic__course')
    return render(request,'studygroups/my_groups.html',{
        'memberships':memberships,
    })

def helper_candidates(group):
    eligible_ids=Confidence.objects.filter(
        topic=group.topic,level=Confidence.CAN_EXPLAIN,willing_to_help=True,
        student__enrollments__course=group.topic.course,
        student__enrollments__status=Enrollment.ACTIVE,
    ).values_list('student_id',flat=True)

    removed_ids=GroupMembership.objects.filter(group=group,status=GroupMembership.REMOVED).values_list('student_id',flat=True)
    users=User.objects.filter(pk__in=eligible_ids,is_active=True).exclude(pk__in=removed_ids)
    result=[]
    for user in users.order_by('first_name','pk'):
        ratings=Feedback.objects.filter(helper=user).aggregate(average=Avg('helpfulness_rating'),count=Count('pk'))
        result.append({'user':user,'average':ratings['average'],'count':ratings['count']})
    return result

@login_required
@require_POST
@transaction.atomic
def invite_group_helper(request,group_id,helper_id):
    group,member=get_group_for_member(request.user,group_id)
    group=StudyGroup.objects.select_for_update().get(pk=group.pk)
    if not group.is_open() or group.topic.is_archived:
        raise PermissionDenied('This group is not accepting invitations.')
    invitation=GroupHelperInvitation.objects.filter(group=group).first()
    if invitation and invitation.status in ['pending','accepted']:
        messages.info(request,'This group already has a helper or a pending invitation.')
    elif helper_id==request.user.pk or helper_id not in [row['user'].pk for row in helper_candidates(group)]:
        raise PermissionDenied('This classmate is not available to explain this topic.')
    else:
        GroupHelperInvitation.objects.update_or_create(group=group,defaults={
            'helper_id':helper_id,'invited_by':request.user,'status':'pending'})
        messages.success(request,'Invitation sent. The helper can accept or decline in their Inbox.')
    return redirect('group_detail',group_id=group.pk)

@login_required
@require_POST
@transaction.atomic
def answer_group_invitation(request,invitation_id,answer):
    invitation=get_object_or_404(GroupHelperInvitation.objects.select_for_update(),
                                 pk=invitation_id,helper=request.user)
    group=StudyGroup.objects.select_for_update().get(pk=invitation.group_id)
    if answer not in ['accept','decline']:
        raise PermissionDenied('Invalid answer.')
    if invitation.status!='pending':
        messages.info(request,'This invitation has already been answered.')
        return redirect('inbox')
    if answer=='decline':
        invitation.status='declined'
    else:
        eligible=request.user.pk in [row['user'].pk for row in helper_candidates(group)]
        if (not eligible or not group.is_open() or group.topic.is_archived
                or group.topic.course.is_archived or not group.joined_memberships().exists()):
            invitation.status='withdrawn'
            invitation.save()
            messages.error(request,'This invitation is no longer available.')
            return redirect('inbox')
        GroupMembership.objects.update_or_create(group=group,student=request.user,
                                                 defaults={'status':GroupMembership.JOINED})
        invitation.status='accepted'
    invitation.save()
    if invitation.status=='accepted':
        messages.success(request,'You joined as the group helper. You can now see the messages and meeting details.')
        return redirect('group_detail',group_id=group.pk)
    return redirect('inbox')

@login_required
@require_POST
def withdraw_group_invitation(request,group_id):
    group,member=get_group_for_member(request.user,group_id)
    GroupHelperInvitation.objects.filter(group=group,status='pending').update(status='withdrawn')
    return redirect('group_detail',group_id=group.pk)

def get_group_for_member(user,group_id):
    group=get_object_or_404(StudyGroup.objects.select_related('topic__course'),pk=group_id)
    get_course_and_membership(user,group.topic.course_id)
    membership=GroupMembership.objects.filter(
        group=group,student=user,status=GroupMembership.JOINED).first()
    if membership is None:
        raise Http404('Group not found')
    return group,membership

def need_help_count(topic):
    return Confidence.objects.filter(
        topic=topic,level=Confidence.NEED_HELP,
        student__enrollments__course=topic.course_id,
        student__enrollments__status=Enrollment.ACTIVE,
    ).count()

def group_prompt(user,topic):
    mine=Confidence.objects.filter(student=user,topic=topic).first()
    if mine is None or mine.level!=Confidence.NEED_HELP:
        return None

    count=need_help_count(topic)
    if count<settings.GROUP_SUGGESTION_THRESHOLD:
        return None

    group=StudyGroup.objects.filter(topic=topic,status=StudyGroup.OPEN).first()
    prompt={
        'topic':topic,
        'need_count':count,
        'group':group,
        'joined_count':0,
        'is_member':False,
        'can_start':group is None,
        'can_join':False,
    }
    if group is not None:
        previous=GroupMembership.objects.filter(group=group,student=user).first()
        prompt['joined_count']=group.joined_count()
        prompt['is_member']=previous is not None and previous.status==GroupMembership.JOINED
        removed=previous is not None and previous.status==GroupMembership.REMOVED
        prompt['can_join']=(not prompt['is_member'] and not removed and not group.is_full())
        prompt['is_full']=group.is_full()
    return prompt

def prompts_for_course(user,course):
    prompts=[]
    for topic in Topic.objects.filter(course=course,is_archived=False):
        prompt=group_prompt(user,topic)
        if prompt is not None:
            prompts.append(prompt)
    return prompts
