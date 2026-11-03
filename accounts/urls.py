from django.urls import path
from . import views

urlpatterns=[
    path('people/',views.people,name='people'),
    path('people/<int:user_id>/',views.public_profile,name='public_profile'),
    path('signup/',views.signup,name='signup'),
    path('login/',views.login_view,name='login'),
    path('logout/',views.logout_view,name='logout'),
    path('profile/',views.profile,name='profile'),
    path('profile/edit/',views.edit_profile,name='edit_profile'),
]
