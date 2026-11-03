from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count,Max,Q
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from accounts.models import User
from courses.models import Confidence,Enrollment
from courses.views import get_course_and_membership,get_topic_and_membership
from studygroups.models import GroupHelperInvitation
from .form import HelpRequestForm,ResponseForm,ResolveForm,FeedbackForm
from .models import HelpRequest,HelpInvitation,Response,expire_old_invitations

def withdraw_pending_invitations(help_request):
    help_request.invitations.filter(status=HelpInvitation.PENDING).update(
        status=HelpInvitation.WITHDRAWN,responded_at=timezone.now())

@login_required
def request_list(request,course_id):
    course,membership=get_course_and_membership(request.user,course_id)

    requests_qs=HelpRequest.objects.filter(topic__course=course).select_related(
        'topic','requester','assigned_helper')

    status=request.GET.get('status','')
    if status in [s for s,label in HelpRequest.STATUS_CHOICES]:
        requests_qs=requests_qs.filter(status=status)
    if request.GET.get('mine')=='1':
        requests_qs=requests_qs.filter(requester=request.user)

    rows=[]
    for r in requests_qs:
        rows.append({'req':r,'asker':r.display_name_for(request.user)})

    return render(request,'helpdesk/request_list.html',{
        'course':course,
        'membership':membership,
        'rows':rows,
        'status':status,
        'mine':request.GET.get('mine')=='1',
        'status_choices':HelpRequest.STATUS_CHOICES,
    })

@login_required
def new_request(request,topic_id):
    topic,course,membership=get_topic_and_membership(request.user,topic_id)
    if topic.is_archived:
        messages.error(request,'This topic is archived, so you cannot ask about it.')
        return redirect('course_detail',course_id=course.id)

    my_rating=Confidence.objects.filter(student=request.user,topic=topic).first()
    if my_rating is None:
        messages.info(request,'Please rate your confidence for this topic first, then ask for help.')
        return redirect('topic_detail',topic_id=topic.id)

    if request.method=='POST':
        form=HelpRequestForm(request.POST,requester=request.user,topic=topic)
        if form.is_valid():
            help_request=form.save(commit=False)
            help_request.requester=request.user
            help_request.topic=topic
            help_request.confidence_before=my_rating.level
            help_request.save()
            messages.success(request,'Your request is posted. Now invite a classmate who can help.')
            return redirect('request_detail',request_id=help_request.id)
    else:
        form=HelpRequestForm(requester=request.user,topic=topic)
    return render(request,'helpdesk/request_form.html',{
        'form':form,
        'topic':topic,
        'course':course,
        'title':'Ask for help',
        'my_rating':my_rating,
    })

@login_required
def edit_request(request,request_id):
    help_request,course,membership=get_request_and_membership(request.user,request_id)
    if help_request.requester!=request.user:
        raise PermissionDenied('Only the person who asked can edit this request.')
    if help_request.status!=HelpRequest.OPEN:
        messages.error(request,'You can only edit a request while it is still open.')
        return redirect('request_detail',request_id=help_request.id)

    if request.method=='POST':
        form=HelpRequestForm(request.POST,instance=help_request)
        if form.is_valid():
            form.save()
            messages.success(request,'Request updated.')
            return redirect('request_detail',request_id=help_request.id)
    else:
        form=HelpRequestForm(instance=help_request)
    return render(request,'helpdesk/request_form.html',{
        'form':form,
        'topic':help_request.topic,
        'course':course,
        'title':'Edit request',
        'editing':True,
    })

@login_required
def request_detail(request,request_id):
    expire_old_invitations()
    help_request,course,membership=get_request_and_membership(request.user,request_id)
    user=request.user

    is_requester=help_request.requester==user
    is_helper=help_request.assigned_helper==user

    if request.method=='POST':
        if not help_request.is_active():
            messages.error(request,'This request is closed, so new replies are not allowed.')
            return redirect('request_detail',request_id=help_request.id)
        form=ResponseForm(request.POST)
        if form.is_valid():
            reply=form.save(commit=False)
            reply.request=help_request
            reply.author=user
            reply.save()
            return redirect('request_detail',request_id=help_request.id)
    else:
        form=ResponseForm()

    replies=[]
    for r in help_request.responses.select_related('author'):
        replies.append({
            'reply':r,
            'name':r.author_name_for(user),
            'is_asker':r.author_id==help_request.requester_id,
            'can_delete':r.author_id==user.id or membership.is_moderator(),
        })

    suggestions=[]
    busy_count=0
    pending_invitations=[]
    if is_requester:
        pending_invitations=list(
            help_request.invitations.filter(status=HelpInvitation.PENDING).select_related('helper'))
        if help_request.status==HelpRequest.OPEN:
            result=find_helpers(help_request)
            suggestions=result['suggestions']
            busy_count=result['busy_count']

    can_give_feedback=(is_requester and help_request.status==HelpRequest.RESOLVED
                       and help_request.assigned_helper is not None
                       and not hasattr(help_request,'feedback'))

    return render(request,'helpdesk/request_detail.html',{
        'help_request':help_request,
        'course':course,
        'membership':membership,
        'asker_name':help_request.display_name_for(user),
        'identity_hidden_from_class':help_request.is_anonymous,
        'is_requester':is_requester,
        'is_helper':is_helper,
        'replies':replies,
        'form':form,
        'suggestions':suggestions,
        'busy_count':busy_count,
        'pending_invitations':pending_invitations,
        'can_invite_more':len(pending_invitations)<settings.MAX_PENDING_INVITATIONS,
        'max_invitations':settings.MAX_PENDING_INVITATIONS,
        'can_give_feedback':can_give_feedback,
        'feedback':getattr(help_request,'feedback',None) if is_requester else None,
    })

@login_required
def delete_response(request,response_id):
    reply=get_object_or_404(Response.objects.select_related('request__topic'),pk=response_id)
    help_request,course,membership=get_request_and_membership(request.user,reply.request_id)
    if reply.author_id!=request.user.id and not membership.is_moderator():
        raise PermissionDenied('You can only delete your own replies.')
    if request.method=='POST':
        reply.delete()
        messages.info(request,'Reply deleted.')
    return redirect('request_detail',request_id=help_request.id)

@login_required
def invite_helper(request,request_id,helper_id):
    expire_old_invitations()
    help_request,course,membership=get_request_and_membership(request.user,request_id)
    if help_request.requester!=request.user:
        raise PermissionDenied('Only the person who asked can invite helpers.')
    if request.method!='POST':
        return redirect('request_detail',request_id=help_request.id)

    if help_request.status!=HelpRequest.OPEN:
        messages.error(request,'You can only invite helpers while the request is open.')
        return redirect('request_detail',request_id=help_request.id)

    pending=help_request.invitations.filter(status=HelpInvitation.PENDING).count()
    if pending>=settings.MAX_PENDING_INVITATIONS:
        messages.error(request,f'You can have at most {settings.MAX_PENDING_INVITATIONS} waiting invitations. '
                                'Wait for an answer or withdraw one.')
        return redirect('request_detail',request_id=help_request.id)

    allowed={s['user'].id:s for s in find_helpers(help_request)['suggestions']}
    suggestion=allowed.get(helper_id)
    if suggestion is None:
        messages.error(request,'This classmate cannot be invited right now.')
        return redirect('request_detail',request_id=help_request.id)
    if suggestion['invited']:
        messages.info(request,'This classmate was already invited.')
        return redirect('request_detail',request_id=help_request.id)

    helper=get_object_or_404(User,pk=helper_id)

    invitation,created=HelpInvitation.objects.get_or_create(request=help_request,helper=helper)
    if not created:
        invitation.status=HelpInvitation.PENDING
        invitation.responded_at=None
        invitation.created_at=timezone.now()
        invitation.save()
    messages.success(request,f'Invitation sent to {helper.display_name()}.')
    return redirect('request_detail',request_id=help_request.id)

@login_required
def withdraw_invitation(request,invitation_id):
    invitation=get_object_or_404(HelpInvitation.objects.select_related('request'),pk=invitation_id)
    help_request=invitation.request
    if help_request.requester!=request.user:
        raise PermissionDenied('Only the person who asked can withdraw an invitation.')
    if request.method=='POST' and invitation.status==HelpInvitation.PENDING:
        invitation.status=HelpInvitation.WITHDRAWN
        invitation.responded_at=timezone.now()
        invitation.save()
        messages.info(request,'Invitation withdrawn.')
    return redirect('request_detail',request_id=help_request.id)

@login_required
def accept_invitation(request,invitation_id):
    expire_old_invitations()
    invitation=get_my_invitation(request.user,invitation_id)
    if request.method!='POST':
        return redirect('inbox')

    with transaction.atomic():
        help_request=HelpRequest.objects.get(pk=invitation.request_id)
        invitation.refresh_from_db()

        active_students=Enrollment.objects.filter(
            course=help_request.topic.course,status=Enrollment.ACTIVE,
            student_id__in=[request.user.pk,help_request.requester_id],
        ).values_list('student_id',flat=True)
        eligible=(request.user.pk in active_students
                  and help_request.requester_id in active_students
                  and not help_request.topic.is_archived
                  and not help_request.topic.course.is_archived)
        if not eligible:
            if invitation.status==HelpInvitation.PENDING:
                invitation.status=HelpInvitation.WITHDRAWN
                invitation.responded_at=timezone.now()
                invitation.save()
            messages.error(request,'This invitation is no longer available.')
        elif invitation.status!=HelpInvitation.PENDING:
            messages.error(request,'This invitation is no longer waiting for an answer.')
        elif help_request.status!=HelpRequest.OPEN:
            messages.error(request,'Sorry, this request is no longer open (someone else may have accepted).')
        elif active_help_count(request.user)>=settings.MAX_ACTIVE_HELPS:
            messages.error(request,f'You are already helping {settings.MAX_ACTIVE_HELPS} classmates. '
                                    'Finish one before accepting another.')
        else:
            now=timezone.now()
            help_request.assigned_helper=request.user
            help_request.assigned_at=now
            help_request.status=HelpRequest.IN_PROGRESS
            help_request.save()
            invitation.status=HelpInvitation.ACCEPTED
            invitation.responded_at=now
            invitation.save()
            withdraw_pending_invitations(help_request)
            messages.success(request,'You accepted. Thank you for helping a classmate!')
            return redirect('request_detail',request_id=help_request.id)
    return redirect('inbox')

@login_required
def decline_invitation(request,invitation_id):
    invitation=get_my_invitation(request.user,invitation_id)
    if request.method=='POST' and invitation.status==HelpInvitation.PENDING:
        invitation.status=HelpInvitation.DECLINED
        invitation.responded_at=timezone.now()
        invitation.save()
        messages.info(request,'Invitation declined. No problem.')
    return redirect('inbox')

@login_required
def step_back(request,request_id):
    help_request,course,membership=get_request_and_membership(request.user,request_id)
    if help_request.assigned_helper!=request.user:
        raise PermissionDenied('Only the assigned helper can step back.')
    if request.method=='POST' and help_request.status==HelpRequest.IN_PROGRESS:
        help_request.invitations.filter(helper=request.user).update(
            status=HelpInvitation.DECLINED,responded_at=timezone.now())
        help_request.assigned_helper=None
        help_request.assigned_at=None
        help_request.status=HelpRequest.OPEN
        help_request.save()
        messages.info(request,'You stepped back. The request is open again.')
        return redirect('inbox')
    return redirect('request_detail',request_id=help_request.id)

@login_required
def cancel_request(request,request_id):
    help_request,course,membership=get_request_and_membership(request.user,request_id)
    if help_request.requester!=request.user:
        raise PermissionDenied('Only the person who asked can cancel this request.')
    if request.method=='POST' and help_request.is_active():
        help_request.status=HelpRequest.CANCELLED
        help_request.save()
        withdraw_pending_invitations(help_request)
        messages.info(request,'Your request was cancelled.')
    return redirect('request_detail',request_id=help_request.id)

@login_required
def resolve_request(request,request_id):
    help_request,course,membership=get_request_and_membership(request.user,request_id)
    if help_request.requester!=request.user:
        raise PermissionDenied('Only the person who asked can mark it as resolved.')
    if not help_request.is_active():
        messages.error(request,'This request is already closed.')
        return redirect('request_detail',request_id=help_request.id)

    if request.method=='POST':
        form=ResolveForm(request.POST)
        if form.is_valid():
            level=form.cleaned_data['confidence_after']
            help_request.confidence_after=level
            help_request.status=HelpRequest.RESOLVED
            help_request.resolved_at=timezone.now()
            help_request.save()
            withdraw_pending_invitations(help_request)

            if form.cleaned_data['update_rating']:
                rating,created=Confidence.objects.get_or_create(
                    student=request.user,topic=help_request.topic,defaults={'level':level})
                rating.level=level
                if level!=Confidence.CAN_EXPLAIN:
                    rating.willing_to_help=False
                rating.save()

            messages.success(request,'Marked as resolved. Glad you got unstuck!')
            if help_request.assigned_helper is not None:
                messages.info(request,'Please tell us how helpful the help was.')
                return redirect('give_feedback',request_id=help_request.id)
            return redirect('request_detail',request_id=help_request.id)
    else:
        form=ResolveForm(initial={'confidence_after':help_request.confidence_before})
    return render(request,'helpdesk/resolve_form.html',{
        'form':form,
        'help_request':help_request,
        'course':course,
    })

@login_required
def give_feedback(request,request_id):
    help_request,course,membership=get_request_and_membership(request.user,request_id)
    if help_request.requester!=request.user:
        raise PermissionDenied('Only the person who asked can give feedback.')
    if help_request.status!=HelpRequest.RESOLVED or help_request.assigned_helper is None:
        messages.error(request,'Feedback is only possible for a resolved request that had a helper.')
        return redirect('request_detail',request_id=help_request.id)
    if hasattr(help_request,'feedback'):
        messages.info(request,'You already gave feedback for this request.')
        return redirect('request_detail',request_id=help_request.id)

    if request.method=='POST':
        form=FeedbackForm(request.POST)
        if form.is_valid():
            feedback=form.save(commit=False)
            feedback.request=help_request
            feedback.author=request.user
            feedback.helper=help_request.assigned_helper
            feedback.save()
            messages.success(request,'Thank you for your feedback!')
            return redirect('request_detail',request_id=help_request.id)
    else:
        form=FeedbackForm()
    return render(request,'helpdesk/feedback_form.html',{
        'form':form,
        'help_request':help_request,
        'course':course,
        'helper_name':help_request.assigned_helper.display_name(),
    })

@login_required
def inbox(request):
    expire_old_invitations()
    user=request.user

    invitations=HelpInvitation.objects.filter(
        helper=user,status=HelpInvitation.PENDING,request__status=HelpRequest.OPEN,
        request__topic__course__is_archived=False,
    ).select_related('request__topic__course','request__requester')
    invitation_rows=[{
        'invitation':inv,
        'asker':inv.request.display_name_for(user),
        'busy':active_help_count(user)>=settings.MAX_ACTIVE_HELPS,
    } for inv in invitations]

    helping=HelpRequest.objects.filter(
        assigned_helper=user,status=HelpRequest.IN_PROGRESS
    ).select_related('topic__course','requester')
    helping_rows=[{'req':r,'asker':r.display_name_for(user)} for r in helping]

    my_requests=HelpRequest.objects.filter(
        requester=user,status__in=[HelpRequest.OPEN,HelpRequest.IN_PROGRESS]
    ).select_related('topic__course','assigned_helper')

    group_invites=GroupHelperInvitation.objects.filter(helper=user,status='pending',group__status='open',group__topic__is_archived=False,group__topic__course__is_archived=False).select_related('group__topic__course','invited_by')
    return render(request,'helpdesk/inbox.html',{
        'invitation_rows':invitation_rows,
        'helping_rows':helping_rows,
        'my_requests':my_requests,
        'group_invites':group_invites,
        'max_active':settings.MAX_ACTIVE_HELPS,
        'helping_count':len(helping_rows),
    })

def get_request_and_membership(user,request_id):
    help_request=get_object_or_404(
        HelpRequest.objects.select_related('topic__course','requester','assigned_helper'),
        pk=request_id)
    course,membership=get_course_and_membership(user,help_request.topic.course_id)
    return help_request,course,membership

def get_my_invitation(user,invitation_id):
    return get_object_or_404(
        HelpInvitation.objects.select_related('request__topic__course'),
        pk=invitation_id,helper=user)

def active_help_count(user):
    return HelpRequest.objects.filter(assigned_helper=user,
                                      status=HelpRequest.IN_PROGRESS).count()

def _reason(name,workload):
    if workload==0:
        return f'{name} can explain this topic and has no active requests.'
    if workload==1:
        return f'{name} can explain this topic and has 1 active request.'
    return f'{name} can explain this topic and has {workload} active requests.'

def find_helpers(help_request):
    topic=help_request.topic

    willing_ids=Confidence.objects.filter(
        topic=topic,level=Confidence.CAN_EXPLAIN,willing_to_help=True,
        student__enrollments__course=topic.course_id,
        student__enrollments__status=Enrollment.ACTIVE,
    ).exclude(student=help_request.requester).values_list('student_id',flat=True)

    users=User.objects.filter(pk__in=willing_ids,is_active=True).annotate(
        workload=Count('requests_helping',
                       filter=Q(requests_helping__status=HelpRequest.IN_PROGRESS)),
        last_helped=Max('requests_helping__assigned_at'),
    )

    invitations={inv.helper_id:inv.status for inv in help_request.invitations.all()}

    suggestions=[]
    busy_count=0
    for u in users:
        if invitations.get(u.id) in (HelpInvitation.DECLINED,HelpInvitation.ACCEPTED):
            continue
        if u.workload>=settings.MAX_ACTIVE_HELPS:
            busy_count+=1
            continue
        suggestions.append({
            'user':u,
            'workload':u.workload,
            'reason':_reason(u.display_name(),u.workload),
            'invited':invitations.get(u.id)==HelpInvitation.PENDING,
            'last_helped':u.last_helped,
        })

    suggestions.sort(key=lambda s: (s['workload'],
                                    s['last_helped'] is not None,
                                    s['last_helped'].timestamp() if s['last_helped'] else 0))
    return {'suggestions':suggestions,'busy_count':busy_count}

def inbox_badge(request):
    if not request.user.is_authenticated:
        return {}
    expire_old_invitations()
    count=HelpInvitation.objects.filter(
        helper=request.user,status=HelpInvitation.PENDING,
        request__status='open').count()
    count+=GroupHelperInvitation.objects.filter(helper=request.user,status='pending',group__status='open',group__topic__is_archived=False,group__topic__course__is_archived=False).count()
    return {'pending_invitation_count':count}
