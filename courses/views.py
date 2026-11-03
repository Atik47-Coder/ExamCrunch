from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render,redirect,get_object_or_404
from .form import JoinCourseForm
from .models import Course,Enrollment

@login_required
def my_courses(request):
    memberships=Enrollment.objects.filter(
        student=request.user,status=Enrollment.ACTIVE,course__is_archived=False
    ).select_related('course')
    return render(request,'courses/my_courses.html',{
        'memberships':memberships
    })

@login_required
def create_course(request):
    raise PermissionDenied('Courses can only be created in Django admin.')

@login_required
def join_course(request):
    if request.method=='POST':
        form=JoinCourseForm(request.POST)
        if form.is_valid():
            code=form.cleaned_data['invite_code']
            course=Course.objects.filter(invite_code=code,is_archived=False).first()
            if course is None:
                form.add_error('invite_code','No course found with this code. Please check it.')
            else:
                enrollment=Enrollment.objects.filter(student=request.user,course=course).first()
                if enrollment is None:
                    Enrollment.objects.create(student=request.user,course=course)
                    messages.success(request,f'You joined {course}.')
                    return redirect('course_detail',course_id=course.id)
                elif enrollment.status==Enrollment.ACTIVE:
                    messages.info(request,'You are already a member of this course.')
                    return redirect('course_detail',course_id=course.id)
                elif enrollment.status==Enrollment.LEFT:
                    enrollment.status=Enrollment.ACTIVE
                    enrollment.save()
                    messages.success(request,f'Welcome back to {course}.')
                    return redirect('course_detail',course_id=course.id)
                else:
                    form.add_error('invite_code','You were removed from this course. Please ask a moderator.')
    else:
        form=JoinCourseForm()
    return render(request,'courses/join_course.html',{
        'form':form
    })

def get_course_and_membership(user,course_id):
    course=get_object_or_404(Course,pk=course_id,is_archived=False)
    membership=Enrollment.objects.filter(
        student=user,course=course,status=Enrollment.ACTIVE).first()
    if membership is None:
        raise Http404('Course not found')
    return course,membership
