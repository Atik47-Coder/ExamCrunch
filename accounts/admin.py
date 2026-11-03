from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .form import StudentAdminChangeForm,StudentAdminCreationForm
from .models import User

class MyUserAdmin(UserAdmin):
    form=StudentAdminChangeForm
    add_form=StudentAdminCreationForm

    fieldsets=UserAdmin.fieldsets + (
        ('ExamCrunch',{'fields':('student_id','bio','profile_image')}),
    )
    add_fieldsets=UserAdmin.add_fieldsets + (
        ('ExamCrunch',{'fields':('student_id','email')}),
        ('Account type',{'fields':('is_staff','is_superuser')}),
    )
    list_display=['username','student_id','email','is_active','is_staff']
    search_fields=['username','student_id','email']

admin.site.register(User,MyUserAdmin)
