import re

from django.core.exceptions import ValidationError

STUDENT_EMAIL_DOMAIN='uap-bd.edu'
STUDENT_ID_DIGITS=8

STUDENT_ID_RE=re.compile(r'[0-9]{%d}' % STUDENT_ID_DIGITS)
STUDENT_EMAIL_RE=re.compile(
    r'(?P<student_id>[0-9]{%d})@%s' % (STUDENT_ID_DIGITS,re.escape(STUDENT_EMAIL_DOMAIN))
)

EMAIL_FORMAT_MESSAGE=(
    'Use your student email: exactly %d digits followed by @%s '
    '(for example 24101009@%s).' % (STUDENT_ID_DIGITS,STUDENT_EMAIL_DOMAIN,STUDENT_EMAIL_DOMAIN)
)
STUDENT_ID_FORMAT_MESSAGE='Your student ID must be exactly %d digits.' % STUDENT_ID_DIGITS
ID_MISMATCH_MESSAGE='The digits in your email must match your student ID.'

def normalize_email(value):
    return (value or '').strip().lower()

def normalize_student_id(value):
    return (value or '').strip()

def is_student_account(user):
    return not (user.is_staff or user.is_superuser)

def validate_student_identity(email,student_id):
    email=normalize_email(email)
    student_id=normalize_student_id(student_id)
    errors={}

    email_match=STUDENT_EMAIL_RE.fullmatch(email) if email else None
    if not email:
        errors['email']='Email is required.'
    elif not email_match:
        errors['email']=EMAIL_FORMAT_MESSAGE

    if not student_id:
        errors['student_id']='Student ID is required.'
    elif not STUDENT_ID_RE.fullmatch(student_id):
        errors['student_id']=STUDENT_ID_FORMAT_MESSAGE

    if not errors and email_match.group('student_id')!=student_id:
        errors['email']=ID_MISMATCH_MESSAGE

    if errors:
        raise ValidationError(errors)
    return email,student_id
