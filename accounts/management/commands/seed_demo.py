from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone

from accounts.models import User
from accounts.validators import STUDENT_EMAIL_DOMAIN
from courses.models import Course,Enrollment,Topic,Confidence

PASSWORD='Demo!pass123'
STUDENTS=[
    ('mahin','Mahin','Khan'),('sara','Sara','Ahmed'),('rafi','Rafi','Hasan'),
    ('nila','Nila','Rahman'),('tamim','Tamim','Iqbal'),('lina','Lina','Das'),
]
TOPICS=[
    ('Exception Handling','try, except, finally and custom exceptions',[1,1,1,3,2,2]),
    ('Polymorphism','Method overriding and duck typing',[3,3,2,1,3,2]),
    ('Abstraction','Abstract classes and interfaces',[1,2,None,None,None,None]),
    ('File Handling','Reading and writing files',[None] * 6),
]

def demo_student_id(index):
    return f'2410{index:04d}'

def demo_email(index):
    return f'{demo_student_id(index)}@{STUDENT_EMAIL_DOMAIN}'

def old_demo_email(username):
    return f'{username}@example.com'

class Command(BaseCommand):
    help='Creates demo students, one course and some topic ratings (safe to run twice).'

    def add_arguments(self,parser):
        parser.add_argument('--password',default=PASSWORD,
                            help='Password for NEW demo accounts (default: %s).' % PASSWORD)
        parser.add_argument('--upgrade-legacy-demo',action='store_true',
                            help='Change the email of demo accounts made by an older seed_demo '
                                 '(<name>@example.com) to the new student email.')
        parser.add_argument('--allow-non-debug',action='store_true',
                            help='Allow running when DEBUG is False (never do this on a real site).')

    def handle(self,*args,**options):
        if not settings.DEBUG and not options['allow_non_debug']:
            raise CommandError('seed_demo creates fake accounts with a public password, so it only '
                               'runs when DEBUG=True. Use --allow-non-debug if you really mean it.')

        users={}
        for i,(username,first,last) in enumerate(STUDENTS):
            users[username]=self.get_or_create_demo_user(
                username,first,last,i,options['password'],options['upgrade_legacy_demo'])

        course,_=Course.objects.get_or_create(code='CSE 2101',section='A',defaults={
            'title':'Object Oriented Programming','semester':'Fall 2026',
            'description':'Exam revision course for OOP in Python.','created_by':users['mahin'],
            'exam_date':timezone.localdate() + timedelta(days=14)})
        for username,user in users.items():
            Enrollment.objects.get_or_create(student=user,course=course,defaults={
                'role':Enrollment.MODERATOR if username=='mahin' else Enrollment.MEMBER})

        for order,(title,description,levels) in enumerate(TOPICS):
            topic,_=Topic.objects.get_or_create(course=course,title=title,defaults={
                'description':description,'display_order':order})
            for (username,_,_),level in zip(STUDENTS,levels):
                if level:
                    Confidence.objects.get_or_create(student=users[username],topic=topic,defaults={
                        'level':level,'willing_to_help':level==3})

        emails=', '.join(demo_email(i) for i in range(len(STUDENTS)))
        self.stdout.write(self.style.SUCCESS(
            f'Demo ready. Log in with one of these emails: {emails}'))
        self.stdout.write(f'Demo password for accounts created by this command: {options['password']}')
        self.stdout.write(f'Course invite code: {course.invite_code}')

    def get_or_create_demo_user(self,username,first,last,index,password,upgrade_legacy):
        student_id,email=demo_student_id(index),demo_email(index)

        existing=User.objects.filter(email__iexact=email).first()
        if existing:
            if existing.username!=username or existing.student_id!=student_id:
                raise CommandError(f'{email} already belongs to a different account '
                                   f'({existing.username!r}); not touching it.')
            return existing

        legacy=User.objects.filter(username=username).first()
        if legacy:
            is_old_demo=legacy.student_id==student_id and legacy.email==old_demo_email(username)
            if not is_old_demo:
                raise CommandError(f'A real account with username {username!r} already exists; '
                                   f'not reusing it as a demo account.')
            if upgrade_legacy:
                legacy.email=email
                legacy.save()
                self.stdout.write(f'Updated old demo account {username!r}: email is now {email}')
            else:
                self.stdout.write(self.style.WARNING(
                    f'Old demo account {username!r} still has email {legacy.email!r}. '
                    f'Run again with --upgrade-legacy-demo to switch it to {email}.'))
            return legacy

        if User.objects.filter(student_id=student_id).exists():
            raise CommandError(f'Student ID {student_id} already belongs to another account; '
                               f'not creating demo account {username!r}.')
        user=User(username=username,first_name=first,last_name=last,
                  email=email,student_id=student_id)
        user.set_password(password)
        user.save()
        return user
