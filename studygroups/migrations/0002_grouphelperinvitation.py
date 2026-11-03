import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('studygroups', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupHelperInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined'), ('withdrawn', 'Withdrawn')], default='pending', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('group', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='helper_invitation', to='studygroups.studygroup')),
                ('helper', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_invitations', to=settings.AUTH_USER_MODEL)),
                ('invited_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_invitations_sent', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
