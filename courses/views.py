from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count,Q
from django.http import Http404,FileResponse
from django.shortcuts import render,redirect,get_object_or_404
from .form import CourseForm,JoinCourseForm,ConfidenceForm,ResourceForm
from .models import Course,Enrollment,Topic,Confidence,Resource

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

@login_required
def add_topic(request,course_id):
    raise PermissionDenied('Topics can only be managed in Django admin.')

@login_required
def edit_topic(request,topic_id):
    raise PermissionDenied('Topics can only be managed in Django admin.')

@login_required
def toggle_topic(request,topic_id):
    raise PermissionDenied('Topics can only be managed in Django admin.')

@login_required
def topic_detail(request,topic_id):
    from studygroups.views import group_prompt
    topic,course,membership=get_topic_and_membership(request.user,topic_id)
    if topic.is_archived and not membership.is_moderator():
        raise Http404('Topic not found')

    my_rating=Confidence.objects.filter(student=request.user,topic=topic).first()

    if request.method=='POST':
        form=ConfidenceForm(request.POST,instance=my_rating)
        if form.is_valid():
            rating=form.save(commit=False)
            rating.student=request.user
            rating.topic=topic
            rating.save()
            messages.success(request,'Your confidence was saved. Only you can see it.')
            return redirect('topic_detail',topic_id=topic.id)
    else:
        form=ConfidenceForm(instance=my_rating)

    active_students=Enrollment.objects.filter(course=course,status=Enrollment.ACTIVE).count()
    snapshot=topic_stats(Topic.objects.filter(pk=topic.pk),active_students)[0]

    resource_rows=[{'resource':r,'can_manage':can_manage_resource(request.user,r,membership)}
                   for r in Resource.objects.filter(topic=topic).select_related('uploaded_by')]

    return render(request,'courses/topic_detail.html',{
        'topic':topic,
        'course':course,
        'membership':membership,
        'form':form,
        'my_rating':my_rating,
        'snapshot':snapshot,
        'resource_rows':resource_rows,
        'group_prompt':group_prompt(request.user,topic),
        'min_ratings':settings.MIN_RATINGS_FOR_DASHBOARD,
    })

@login_required
def course_dashboard(request,course_id):
    course,membership=get_course_and_membership(request.user,course_id)
    rows=course_stats(course)

    visible=[r for r in rows if r['show_counts'] and r['need_help']>0]
    hardest=max(visible,key=lambda r: (r['need_help_pct'],r['need_help'])) if visible else None
    return render(request,'courses/dashboard.html',{
        'hardest':hardest,
        'course':course,
        'membership':membership,
        'rows':rows,
        'min_ratings':settings.MIN_RATINGS_FOR_DASHBOARD,
    })

@login_required
def resource_list(request,course_id):
    course,membership=get_course_and_membership(request.user,course_id)
    topics=Topic.objects.filter(course=course,is_archived=False)
    groups=[]
    for topic in topics:
        rows=[{'resource':r,'can_manage':can_manage_resource(request.user,r,membership)}
              for r in Resource.objects.filter(topic=topic).select_related('uploaded_by')]
        groups.append({'topic':topic,'rows':rows})
    return render(request,'courses/resource_list.html',{
        'course':course,
        'membership':membership,
        'groups':groups,
    })

@login_required
def add_resource(request,topic_id):
    topic,course,membership=get_topic_and_membership(request.user,topic_id)
    if topic.is_archived:
        raise Http404('Topic not found')

    if request.method=='POST':
        form=ResourceForm(request.POST,request.FILES)
        if form.is_valid():
            resource=form.save(commit=False)
            resource.topic=topic
            resource.uploaded_by=request.user
            resource.save()
            messages.success(request,'Resource shared with your classmates.')
            return redirect('topic_detail',topic_id=topic.id)
    else:
        form=ResourceForm()
    return render(request,'courses/resource_form.html',{
        'form':form,'topic':topic,'course':course,'title':'Share a resource',
    })

@login_required
def edit_resource(request,resource_id):
    resource,course,membership=get_resource_and_membership(request.user,resource_id)
    if not can_manage_resource(request.user,resource,membership):
        raise PermissionDenied('Only the uploader or a moderator can edit this resource.')

    old_file_name=resource.file.name
    if request.method=='POST':
        form=ResourceForm(request.POST,request.FILES,instance=resource)
        if form.is_valid():
            resource=form.save()

            if old_file_name and resource.file.name!=old_file_name:
                resource.file.storage.delete(old_file_name)
            messages.success(request,'Resource updated.')
            return redirect('topic_detail',topic_id=resource.topic_id)
    else:
        form=ResourceForm(instance=resource)
    return render(request,'courses/resource_form.html',{
        'form':form,'topic':resource.topic,'course':course,
        'title':'Edit resource','resource':resource,
    })

@login_required
def delete_resource(request,resource_id):
    resource,course,membership=get_resource_and_membership(request.user,resource_id)
    if not can_manage_resource(request.user,resource,membership):
        raise PermissionDenied('Only the uploader or a moderator can delete this resource.')
    topic_id=resource.topic_id
    if request.method=='POST':
        if resource.file:
            resource.file.delete(save=False)
        resource.delete()
        messages.info(request,'Resource deleted.')
    return redirect('topic_detail',topic_id=topic_id)

@login_required
def download_resource(request,resource_id):
    resource,course,membership=get_resource_and_membership(request.user,resource_id)
    if not resource.file:
        raise Http404('This resource has no file.')
    try:
        file=resource.file.open('rb')
    except FileNotFoundError:
        raise Http404('The file is missing.')

    return FileResponse(file,as_attachment=True,filename=resource.file_name())

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

def get_topic_and_membership(user,topic_id):
    topic=get_object_or_404(Topic,pk=topic_id)
    course,membership=get_course_and_membership(user,topic.course_id)
    return topic,course,membership

def get_topic_as_moderator(user,topic_id):
    topic,course,membership=get_topic_and_membership(user,topic_id)
    if not membership.is_moderator():
        raise PermissionDenied('Only moderators can do this.')
    return topic,course,membership

def get_resource_and_membership(user,resource_id):
    resource=get_object_or_404(Resource.objects.select_related('topic__course','uploaded_by'),
                               pk=resource_id)
    course,membership=get_course_and_membership(user,resource.topic.course_id)
    return resource,course,membership

def can_manage_resource(user,resource,membership):
    return resource.uploaded_by_id==user.id or membership.is_moderator()

def topic_stats(topics,active_students):
    topics=topics.annotate(
        rated=Count('confidences'),
        need_help=Count('confidences',filter=Q(confidences__level=Confidence.NEED_HELP)),
        practising=Count('confidences',filter=Q(confidences__level=Confidence.PRACTISING)),
        can_explain=Count('confidences',filter=Q(confidences__level=Confidence.CAN_EXPLAIN)),
        willing=Count('confidences',filter=Q(confidences__willing_to_help=True)),
    )

    rows=[]
    for t in topics:
        show=t.rated>=settings.MIN_RATINGS_FOR_DASHBOARD
        row={
            'topic':t,
            'rated':t.rated,
            'students':active_students,
            'show_counts':show,
            'participation':round(t.rated * 100 / active_students) if active_students else 0,
        }
        if show:
            row.update({
                'need_help':t.need_help,
                'practising':t.practising,
                'can_explain':t.can_explain,
                'willing':t.willing,
                'need_help_pct':round(t.need_help * 100 / t.rated),
                'practising_pct':round(t.practising * 100 / t.rated),
            })

            row['can_explain_pct']=100 - row['need_help_pct'] - row['practising_pct']
        rows.append(row)
    return rows

def course_stats(course):
    active_students=Enrollment.objects.filter(course=course,status=Enrollment.ACTIVE).count()
    topics=Topic.objects.filter(course=course,is_archived=False)
    return topic_stats(topics,active_students)
