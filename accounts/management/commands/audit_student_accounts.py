from django.core.management.base import BaseCommand,CommandError

from accounts.models import User
from accounts.validators import STUDENT_EMAIL_RE,STUDENT_ID_RE,normalize_email

def describe(user):
    return 'id=%s username=%r email=%r student_id=%r%s%s' % (
        user.pk,user.username,user.email,user.student_id,
        ' [admin]' if (user.is_staff or user.is_superuser) else '',
        '' if user.is_active else ' [inactive]')

class Command(BaseCommand):
    help=('Read-only report of accounts that break the student email / ID rules. '
          'Run it BEFORE upgrading an existing database. Exit status is non-zero '
          'if accounts share an email (that blocks the upgrade).')

    def handle(self,*args,**options):
        users=list(User.objects.order_by('pk'))
        blocking=0
        notices=0

        by_email={}
        for user in users:
            if user.email.strip():
                by_email.setdefault(normalize_email(user.email),[]).append(user)
        duplicates={k:v for k,v in by_email.items() if len(v)>1}
        self.stdout.write(self.style.MIGRATE_HEADING('Shared emails (BLOCK the upgrade)'))
        if duplicates:
            for email,rows in sorted(duplicates.items()):
                blocking+=1
                self.stdout.write(self.style.ERROR('  %s' % email))
                for user in rows:
                    self.stdout.write('    %s' % describe(user))
        else:
            self.stdout.write('  none')

        self.stdout.write(self.style.MIGRATE_HEADING('Student accounts that do not meet the policy (should be corrected)'))
        problems=[]
        for user in users:
            if user.is_staff or user.is_superuser:
                continue
            email=normalize_email(user.email)
            student_id=(user.student_id or '').strip()
            email_match=STUDENT_EMAIL_RE.fullmatch(email)
            reasons=[]
            if not email:
                reasons.append('no email')
            elif not email_match:
                reasons.append('email is not <8 digits>@uap-bd.edu')
            if not student_id:
                reasons.append('no student ID')
            elif not STUDENT_ID_RE.fullmatch(student_id):
                reasons.append('student ID is not 8 digits')
            if email_match and STUDENT_ID_RE.fullmatch(student_id) and email_match.group('student_id')!=student_id:
                reasons.append('email digits do not match student ID')
            if reasons:
                problems.append((user,reasons))
        for user,reasons in problems:
            notices+=1
            self.stdout.write('  %s -> %s' % (describe(user),'; '.join(reasons)))
        if not problems:
            self.stdout.write('  none')

        no_email=[u for u in users if not u.email.strip() and (u.is_staff or u.is_superuser)]
        if no_email:
            self.stdout.write(self.style.MIGRATE_HEADING('Administrator accounts without an email (allowed)'))
            for user in no_email:
                self.stdout.write('  %s' % describe(user))

        self.stdout.write('')
        self.stdout.write('%d account(s) checked. %d shared-email group(s) (blocking), %d student account(s) to correct.'
                          % (len(users),blocking,notices))
        if blocking:
            raise CommandError('Resolve the shared emails above before running "migrate".')
