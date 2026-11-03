from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path,include

from . import views

urlpatterns=[
    path('admin/',admin.site.urls),
    path('accounts/',include('accounts.urls')),
    path('courses/',include('courses.urls')),
    path('help/',include('helpdesk.urls')),
    path('groups/',include('studygroups.urls')),
    path('',views.home,name='home'),
]

if settings.DEBUG:
    urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
