from django.urls import path
from . import views

urlpatterns=[
    path('',views.my_courses,name='my_courses'),
    path('create/',views.create_course,name='create_course'),
    path('join/',views.join_course,name='join_course'),
]
