import accounts.models
import django.db.models.functions.text
from django.db import migrations, models

def refuse_if_duplicate_emails(apps, schema_editor):

    User = apps.get_model("accounts", "User")
    seen = {}
    for pk, username, email in (
        User.objects.exclude(email="").order_by("pk").values_list("pk", "username", "email")
    ):
        seen.setdefault(email.strip().lower(), []).append((pk, username, email))
    duplicates = {key: rows for key, rows in seen.items() if len(rows) > 1}
    if duplicates:
        lines = []
        for key, rows in sorted(duplicates.items()):
            who = ", ".join("id=%s username=%r email=%r" % row for row in rows)
            lines.append("  - %s: %s" % (key, who))
        raise RuntimeError(
            "Cannot add the unique-email rule: these accounts share an email "
            "(ignoring upper/lower case).\n%s\n"
            "Nothing was changed. Fix the duplicates (for example in the Django admin: "
            "correct the email, or deactivate the account that is not needed), run "
            "'python manage.py audit_student_accounts' to check, then run "
            "'python manage.py migrate' again." % "\n".join(lines)
        )

class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(refuse_if_duplicate_emails, migrations.RunPython.noop),
        migrations.AlterModelManagers(
            name="user",
            managers=[
                ("objects", accounts.models.UserManager()),
            ],
        ),
        migrations.AlterField(
            model_name="user",
            name="student_id",
            field=models.CharField(
                blank=True,
                help_text="Students: exactly 8 digits, saved as text. Leave empty for administrator accounts.",
                max_length=20,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("email"),
                condition=models.Q(("email", ""), _negated=True),
                name="accounts_user_email_ci_unique",
                violation_error_message="An account with this email already exists.",
            ),
        ),
    ]
