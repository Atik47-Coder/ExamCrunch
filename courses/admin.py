from django.contrib import admin
from django import forms
from .models import Course,Enrollment,Topic,Confidence,Resource

class EnrollmentInline(admin.TabularInline):
    model=Enrollment
    extra=0

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display=('code','title','semester','is_archived')
    readonly_fields=('created_by','invite_code')
    inlines=[EnrollmentInline]

    def save_model(self,request,obj,form,change):
        if not change:
            obj.created_by=request.user
        super().save_model(request,obj,form,change)
        if not change:
            Enrollment.objects.create(course=obj,student=request.user,
                                      role=Enrollment.MODERATOR)

admin.site.register(Enrollment)

class TopicAdminForm(forms.ModelForm):
    class Meta:
        model=Topic
        fields='__all__'

    def clean(self):
        cleaned=super().clean()
        title=(cleaned.get('title') or '').strip()
        course=cleaned.get('course')
        cleaned['title']=title
        if course and title:
            duplicates=Topic.objects.filter(course=course,title__iexact=title).exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error('title','This course already has a topic with this title.')
        return cleaned

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    form=TopicAdminForm
    list_display=('title','course','display_order','is_archived')
    list_filter=('course','is_archived')
    search_fields=('title','course__code')

admin.site.register(Confidence)
admin.site.register(Resource)
