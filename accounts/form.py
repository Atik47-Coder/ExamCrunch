from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AdminUserCreationForm,UserChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from examcrunch.bootstrap import style_form
from .models import User
from .validators import (
    EMAIL_FORMAT_MESSAGE,ID_MISMATCH_MESSAGE,STUDENT_EMAIL_DOMAIN,STUDENT_EMAIL_RE,
    STUDENT_ID_FORMAT_MESSAGE,STUDENT_ID_RE,normalize_email,normalize_student_id,
    validate_student_identity,
)

DUPLICATE_EMAIL_MESSAGE='An account with this email already exists. Try logging in instead.'
DUPLICATE_ID_MESSAGE='An account with this student ID already exists. Try logging in instead.'
DUPLICATE_GENERIC_MESSAGE=('An account with this email or student ID already exists. '
                           'Try logging in instead.')

class SignUpForm(forms.ModelForm):
    password1=forms.CharField(label='Password',widget=forms.PasswordInput)
    password2=forms.CharField(label='Confirm password',widget=forms.PasswordInput)

    class Meta:
        model=User
        fields=['first_name','last_name','student_id','email']

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        for name in ['first_name','last_name','student_id','email']:
            self.fields[name].required=True
        self.fields['student_id'].label='Student ID'
        self.fields['student_id'].help_text='Exactly 8 digits, e.g. 24101009'
        self.fields['email'].label='Student email'
        self.fields['email'].help_text='ID + @%s, e.g. 24101009@%s' % (STUDENT_EMAIL_DOMAIN,STUDENT_EMAIL_DOMAIN)
        self.fields['email'].widget.attrs.update({'autocomplete':'email','inputmode':'email'})
        self.fields['student_id'].widget.attrs.update({'inputmode':'numeric','maxlength':'8'})
        self.fields['password1'].widget.attrs['autocomplete']='new-password'
        self.fields['password2'].widget.attrs['autocomplete']='new-password'
        style_form(self)

    def clean_student_id(self):
        student_id=normalize_student_id(self.cleaned_data.get('student_id'))
        if not STUDENT_ID_RE.fullmatch(student_id):
            raise ValidationError(STUDENT_ID_FORMAT_MESSAGE)
        return student_id

    def clean_email(self):
        email=normalize_email(self.cleaned_data.get('email'))
        if not STUDENT_EMAIL_RE.fullmatch(email):
            raise ValidationError(EMAIL_FORMAT_MESSAGE)
        return email

    def _duplicate_errors(self,email,student_id):
        errors={}
        if email and User.objects.filter(email__iexact=email).exists():
            errors['email']=DUPLICATE_EMAIL_MESSAGE
        if student_id and User.objects.filter(student_id=student_id).exists():
            errors['student_id']=DUPLICATE_ID_MESSAGE
        return errors

    def add_duplicate_error(self):
        email=self.cleaned_data.get('email')
        student_id=self.cleaned_data.get('student_id')
        errors=self._duplicate_errors(email,student_id)
        if errors:
            for field,message in errors.items():
                self.add_error(field,message)
        else:
            self.add_error(None,DUPLICATE_GENERIC_MESSAGE)

    def clean(self):
        cleaned=super().clean()
        email=cleaned.get('email')
        student_id=cleaned.get('student_id')

        if email and student_id and email.split('@')[0]!=student_id:
            self.add_error('email',ID_MISMATCH_MESSAGE)
            email=None

        if email or student_id:
            for field,message in self._duplicate_errors(email,student_id).items():
                self.add_error(field,message)

        p1=cleaned.get('password1')
        p2=cleaned.get('password2')
        if p1 and p2 and p1!=p2:
            self.add_error('password2','The two passwords do not match.')
        elif p1:
            candidate=User(
                username=student_id or '',first_name=cleaned.get('first_name',''),
                last_name=cleaned.get('last_name',''),email=cleaned.get('email') or '',
                student_id=student_id,
            )
            try:
                validate_password(p1,user=candidate)
            except ValidationError as error:
                self.add_error('password1',error)
        return cleaned

    def _make_username(self,student_id):
        username,number=student_id,1
        while User.objects.filter(username__iexact=username).exists():
            number+=1
            username='%s-%d' % (student_id,number)
        return username

    def save(self,commit=True):
        user=super().save(commit=False)
        user.username=self._make_username(user.student_id)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user

class EmailLoginForm(forms.Form):
    email=forms.EmailField(label='Email',widget=forms.EmailInput(
        attrs={'autofocus':True,'autocomplete':'email'}))
    password=forms.CharField(label='Password',strip=False,widget=forms.PasswordInput(
        attrs={'autocomplete':'current-password'}))

    error_messages={
        'invalid_login':'Please enter a correct email and password.',
    }

    def __init__(self,request=None,*args,**kwargs):
        self.request=request
        self.user_cache=None
        super().__init__(*args,**kwargs)
        style_form(self)

    def clean_email(self):
        return normalize_email(self.cleaned_data['email'])

    def clean(self):
        cleaned=super().clean()
        email=cleaned.get('email')
        password=cleaned.get('password')
        if email and password:
            self.user_cache=authenticate(self.request,email=email,password=password)
            if self.user_cache is None:
                raise ValidationError(self.error_messages['invalid_login'],code='invalid_login')
        return cleaned

    def get_user(self):
        return self.user_cache

class ProfileForm(forms.ModelForm):
    class Meta:
        model=User
        fields=['first_name','last_name','bio','profile_image']
       

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        style_form(self)

