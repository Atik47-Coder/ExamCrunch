from django.urls import path
from . import views

urlpatterns=[
    path('',views.my_courses,name='my_courses'),
    path('create/',views.create_course,name='create_course'),
    path('join/',views.join_course,name='join_course'),
    path('<int:course_id>/',views.course_detail,name='course_detail'),
    path('<int:course_id>/edit/',views.edit_course,name='edit_course'),
    path('<int:course_id>/new-invite-code/',views.new_invite_code,name='new_invite_code'),
    path('<int:course_id>/dashboard/',views.course_dashboard,name='course_dashboard'),
    path('<int:course_id>/topics/add/',views.add_topic,name='add_topic'),
    path('topics/<int:topic_id>/',views.topic_detail,name='topic_detail'),
    path('topics/<int:topic_id>/edit/',views.edit_topic,name='edit_topic'),
    path('topics/<int:topic_id>/archive/',views.toggle_topic,name='toggle_topic'),
    path('<int:course_id>/resources/',views.resource_list,name='resource_list'),
    path('topics/<int:topic_id>/resources/add/',views.add_resource,name='add_resource'),
    path('resources/<int:resource_id>/edit/',views.edit_resource,name='edit_resource'),
    path('resources/<int:resource_id>/delete/',views.delete_resource,name='delete_resource'),
    path('resources/<int:resource_id>/download/',views.download_resource,name='download_resource'),
]
