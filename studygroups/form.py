from django import forms

from examcrunch.bootstrap import style_form
from .models import StudyGroup,GroupMessage

class GroupInfoForm(forms.ModelForm):
    class Meta:
        model=StudyGroup
        fields=['name','meeting_info']
        widgets={'meeting_info':forms.Textarea(attrs={'rows':3})}
        labels={'meeting_info':'Where and when do you meet?'}
        help_texts={'meeting_info':'For example: "Library, Sunday 3 pm" or a link to your chat group.'}

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        style_form(self)

class GroupMessageForm(forms.ModelForm):
    class Meta:
        model=GroupMessage
        fields=['body']
        widgets={'body':forms.Textarea(attrs={'rows':2,'placeholder':'Write a message to the group...'})}
        labels={'body':''}

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        style_form(self)
