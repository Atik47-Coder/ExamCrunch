from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render,redirect,get_object_or_404
from .form import CourseForm,JoinCourseForm
from .models import Course,Enrollment,Topic,Confidence

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

@login_required
def course_detail(request,course_id):
    from studygroups.views import prompts_for_course
    course,membership=get_course_and_membership(request.user,course_id)

    topics=Topic.objects.filter(course=course,is_archived=False)

    my_ratings={}
    for c in Confidence.objects.filter(student=request.user,topic__in=topics):
        my_ratings[c.topic_id]=c

    topic_rows=[]
    for t in topics:
        topic_rows.append({'topic':t,'rating':my_ratings.get(t.id)})

    member_count=Enrollment.objects.filter(course=course,status=Enrollment.ACTIVE).count()
    rated_count=len(my_ratings)
    total_topics=len(topic_rows)

    my_levels={'need':0,'practising':0,'explain':0}
    for c in my_ratings.values():
        if c.level==Confidence.NEED_HELP:
            my_levels['need']+=1
        elif c.level==Confidence.PRACTISING:
            my_levels['practising']+=1
        else:
            my_levels['explain']+=1

    ring_a=round(my_levels['need'] * 100 / total_topics) if total_topics else 0
    ring_b=ring_a + (round(my_levels['practising'] * 100 / total_topics) if total_topics else 0)
    ring_c=ring_b + (round(my_levels['explain'] * 100 / total_topics) if total_topics else 0)

    archived_topics=[]
    if membership.is_moderator():
        archived_topics=Topic.objects.filter(course=course,is_archived=True)

    return render(request,'courses/course_detail.html',{
        'course':course,
        'membership':membership,
        'topic_rows':topic_rows,
        'archived_topics':archived_topics,
        'member_count':member_count,
        'rated_count':rated_count,
        'my_levels':my_levels,
        'ring_a':ring_a,'ring_b':ring_b,'ring_c':ring_c,
        'total_topics':total_topics,
        'rated_percent':round(rated_count * 100 / total_topics) if total_topics else 0,
        'group_prompts':prompts_for_course(request.user,course),
    })

@login_required
def edit_course(request,course_id):
    course,membership=get_course_as_moderator(request.user,course_id)
    if request.method=='POST':
        form=CourseForm(request.POST,instance=course)
        if form.is_valid():
            form.save()
            messages.success(request,'Course updated.')
            return redirect('course_detail',course_id=course.id)
    else:
        form=CourseForm(instance=course)
    return render(request,'courses/course_form.html',{
        'form':form,
        'title':'Edit course',
        'course':course,
    })

@login_required
def new_invite_code(request,course_id):
    course,membership=get_course_as_moderator(request.user,course_id)
    if request.method=='POST':
        course.make_new_invite_code()
        course.save()
        messages.success(request,f'New invite code: {course.invite_code}. The old code no longer works.')
    return redirect('course_detail',course_id=course.id)

def get_course_and_membership(user,course_id):
    course=get_object_or_404(Course,pk=course_id,is_archived=False)
    membership=Enrollment.objects.filter(
        student=user,course=course,status=Enrollment.ACTIVE).first()
    if membership is None:
        raise Http404('Course not found')
    return course,membership

def get_course_as_moderator(user,course_id):
    course,membership=get_course_and_membership(user,course_id)
    if not membership.is_moderator():
        raise PermissionDenied('Only moderators can do this.')
    return course,membership
