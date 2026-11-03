from urllib.parse import urlsplit
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login,logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError,transaction
from django.db.models import Avg,Count
from django.shortcuts import render,redirect,resolve_url,get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from courses.models import Resource
from helpdesk.models import HelpRequest,Feedback
from studygroups.models import StudyGroup,GroupMembership
from .form import EmailLoginForm,SignUpForm,ProfileForm
from .models import User

EMAIL_BACKEND='accounts.backends.EmailBackend'

def signup(request):
    if request.user.is_authenticated:
        return redirect(get_post_login_url(request))

    if request.method=='POST':
        form=SignUpForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user=form.save()
            except IntegrityError:
                form.add_duplicate_error()
            else:
                login(request,user,backend=EMAIL_BACKEND)
                messages.success(request,'Welcome to ExamCrunch! Join a course with an invitation code to begin.')
                return redirect(get_post_login_url(request))
    else:
        form=SignUpForm()
    return render(request,'accounts/signup.html',{
        'form':form
    })

def login_view(request):
    if request.user.is_authenticated:
        return redirect(get_post_login_url(request))

    if request.method=='POST':
        form=EmailLoginForm(request,data=request.POST)
        if form.is_valid():
            login(request,form.get_user())
            return redirect(get_post_login_url(request))
    else:
        form=EmailLoginForm(request)
    return render(request,'accounts/login.html',{
        'form':form,
        'next_url':get_safe_next_url(request),
    })

def logout_view(request):
    if request.method=='POST':
        logout(request)
        messages.info(request,'You have been logged out.')
    return redirect('home')

@login_required
def profile(request):
    return show_profile(request,request.user)

@login_required
def edit_profile(request):
    if request.method=='POST':
        form=ProfileForm(request.POST,request.FILES,instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request,'Your profile was updated.')
            return redirect('profile')
    else:
        form=ProfileForm(instance=request.user)
    return render(request,'accounts/edit_profile.html',{
        'form':form
    })

def show_profile(request,student):

    completed=HelpRequest.objects.filter(assigned_helper=student,status=HelpRequest.RESOLVED)
    feedback=Feedback.objects.filter(helper=student)
    average=feedback.aggregate(avg=Avg('helpfulness_rating'))['avg']
    own=student.pk==request.user.pk
    badges=badges_for(student)
    return render(request,'accounts/profile.html',{
        'student':student,'own_profile':own,
        'badges':badges if own else [b for b in badges if b['earned']],
        'helped_count':completed.values('requester_id').distinct().count(),
        'resolved_count':completed.count(),'rating_count':feedback.count(),
        'average_rating':round(average,1) if average is not None else None,
    })

@login_required
def public_profile(request,user_id):
    return show_profile(request,get_object_or_404(User,pk=user_id,is_active=True))

def get_safe_next_url(request):
    candidate=request.POST.get('next') or request.GET.get('next') or ''
    candidate=candidate.strip()
    if not candidate:
        return ''
    if not url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return ''
    parts=urlsplit(candidate)
    if not parts.netloc and not parts.path.startswith('/'):
        return ''
    return candidate

def get_post_login_url(request):
    return get_safe_next_url(request) or resolve_url(settings.LOGIN_REDIRECT_URL)

def badges_for(user):
    helped=HelpRequest.objects.filter(assigned_helper=user,status=HelpRequest.RESOLVED).values('requester_id').distinct().count()
    feedback=Feedback.objects.filter(helper=user).aggregate(avg=Avg('helpfulness_rating'),n=Count('id'))
    climbed=[r for r in HelpRequest.objects.filter(requester=user,status=HelpRequest.RESOLVED,
                                                   confidence_after__isnull=False)
             if r.confidence_after>r.confidence_before]
    shared=Resource.objects.filter(uploaded_by=user).count()
    in_group=GroupMembership.objects.filter(student=user).count()
    started_group=StudyGroup.objects.filter(created_by=user).count()

    rules=[
        ('bi-hand-thumbs-up','First helper','Help one classmate until the request is resolved',helped>=1),
        ('bi-trophy','Super helper','Help 5 classmates',helped>=5),
        ('bi-star-fill','Top rated','Average feedback of 4.5 or more (at least 3 feedbacks)',
         feedback['n']>=3 and (feedback['avg'] or 0)>=4.5),
        ('bi-graph-up-arrow','Climber','Get help and rise to a higher confidence level',len(climbed)>=1),
        ('bi-collection','Note sharer','Share 3 resources',shared>=3),
        ('bi-people','Team player','Join or start a study group',(in_group + started_group)>=1),
    ]
    return [{'icon':i,'name':n,'how':h,'earned':e} for i,n,h,e in rules]
