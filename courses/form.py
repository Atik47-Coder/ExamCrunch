from django import forms
from django.conf import settings

from examcrunch.bootstrap import style_form
from .models import Course,Topic,Confidence,Resource

class CourseForm(forms.ModelForm):
    class Meta:
        model=Course
        fields=['code','title','semester','section','exam_date','description']
        widgets={
            'description':forms.Textarea(attrs={'rows':3}),
            'exam_date':forms.DateInput(attrs={'type':'date'}),
        }
        help_texts={'exam_date':'Optional. Shows a countdown to the exam.'}

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        style_form(self)

class JoinCourseForm(forms.Form):
    invite_code=forms.CharField(max_length=12,label='Invite code')

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        style_form(self)

    def clean_invite_code(self):
        return self.cleaned_data['invite_code'].strip().upper()

class TopicForm(forms.ModelForm):
    class Meta:
        model=Topic
        fields=['title','description','display_order']
        widgets={'description':forms.Textarea(attrs={'rows':3})}
        help_texts={'display_order':'Smaller numbers are shown first.'}

    def __init__(self,*args,**kwargs):
        self.course=kwargs.pop('course')
        super().__init__(*args,**kwargs)
        style_form(self)

    def clean_title(self):
        title=self.cleaned_data['title'].strip()
        same_title=Topic.objects.filter(course=self.course,title__iexact=title)
        if self.instance.pk:
            same_title=same_title.exclude(pk=self.instance.pk)
        if same_title.exists():
            raise forms.ValidationError('This course already has a topic with this title.')
        return title

class ConfidenceForm(forms.ModelForm):
    class Meta:
        model=Confidence
        fields=['level','willing_to_help']
        widgets={'level':forms.RadioSelect}
        labels={'willing_to_help':'I am willing to help classmates with this topic'}

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.fields['level'].choices=Confidence.LEVEL_CHOICES
        style_form(self)

    def clean(self):
        cleaned=super().clean()

        if cleaned.get('level')!=Confidence.CAN_EXPLAIN:
            cleaned['willing_to_help']=False
        return cleaned

class ResourceForm(forms.ModelForm):
    class Meta:
        model=Resource
        fields=['title','description','file','external_url']
        widgets={
            'description':forms.Textarea(attrs={'rows':3}),
            'file':forms.FileInput,
        }
        labels={'external_url':'Link (optional if you upload a file)','file':'File (optional if you add a link)'}

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        style_form(self)

    def clean_file(self):
        file=self.cleaned_data.get('file')

        if file and hasattr(file,'content_type'):
            extension=file.name.rsplit('.',1)[-1].lower() if '.' in file.name else ''
            if extension not in settings.RESOURCE_ALLOWED_EXTENSIONS:
                allowed=', '.join(settings.RESOURCE_ALLOWED_EXTENSIONS)
                raise forms.ValidationError(f'This file type is not allowed. Allowed: {allowed}.')
            if file.size>settings.RESOURCE_MAX_MB * 1024 * 1024:
                raise forms.ValidationError(f'The file is too big. The limit is {settings.RESOURCE_MAX_MB} MB.')
        return file

    def clean_external_url(self):
        url=self.cleaned_data.get('external_url','')
        if url and not url.lower().startswith(('http://','https://')):
            raise forms.ValidationError('The link must start with http:// or https://')
        return url

    def clean(self):
        cleaned=super().clean()

        if not cleaned.get('file') and not cleaned.get('external_url'):
            raise forms.ValidationError('Please upload a file or add a link.')
        return cleaned
