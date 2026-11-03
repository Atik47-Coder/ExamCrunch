from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("helpdesk", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="helpinvitation",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("accepted", "Accepted"),
                    ("declined", "Declined"),
                    ("withdrawn", "Withdrawn"),
                    ("expired", "Expired"),
                ],
                default="pending",
                max_length=10,
            ),
        ),
    ]
