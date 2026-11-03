from django import forms

from courses.models import Confidence
from examcrunch.bootstrap import style_form
from .models import HelpRequest,Response,Feedback

class HelpRequestForm(forms.ModelForm):
    class Meta:
        model=HelpRequest
        fields=['title','description','is_anonymous']
        widgets={'description':forms.Textarea(attrs={'rows':5})}
        labels={'is_anonymous':'Post anonymously (classmates will see "Anonymous student")'}
        help_texts={
            'title':'A short question, e.g. "When does finally run?"',
            'description':'What did you try? What exactly confuses you?',
        }

    def __init__(self,*args,**kwargs):
        self.requester=kwargs.pop('requester',None)
        self.topic=kwargs.pop('topic',None)
        super().__init__(*args,**kwargs)
        style_form(self)

    def clean(self):
        cleaned=super().clean()

        if self.requester and self.topic and not self.instance.pk:
            already=HelpRequest.objects.filter(
                requester=self.requester,topic=self.topic,
                status__in=[HelpRequest.OPEN,HelpRequest.IN_PROGRESS]).exists()
            if already:
                raise forms.ValidationError(
                    'You already have an active request for this topic. '
                    'Resolve or cancel it before asking again.')
        return cleaned

class ResponseForm(forms.ModelForm):
    class Meta:
        model=Response
        fields=['body']
        widgets={'body':forms.Textarea(attrs={'rows':3,'placeholder':'Write a reply...'})}
        labels={'body':''}

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        style_form(self)

class ResolveForm(forms.Form):
    confidence_after=forms.TypedChoiceField(
        choices=Confidence.LEVEL_CHOICES,coerce=int,widget=forms.RadioSelect,
        label='How confident are you about this topic now?')
    update_rating=forms.BooleanField(
        required=False,initial=True,
        label='Also update my private rating for this topic to this level')

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        style_form(self)

class FeedbackForm(forms.ModelForm):
    helpfulness_rating=forms.TypedChoiceField(
        choices=[(i,str(i)) for i in range(1,6)],coerce=int,widget=forms.RadioSelect,
        label='How helpful was the help? (1 = not helpful, 5 = very helpful)')

    class Meta:
        model=Feedback
        fields=['helpfulness_rating','comment']
        widgets={'comment':forms.Textarea(attrs={'rows':3})}
        labels={'comment':'Comment (optional)'}

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        style_form(self)
