from urllib.parse import urlsplit
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login,logout
from django.db import IntegrityError,transaction
from django.shortcuts import render,redirect,resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from .form import EmailLoginForm,SignUpForm

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
