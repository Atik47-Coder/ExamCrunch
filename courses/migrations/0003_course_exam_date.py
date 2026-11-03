from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0002_resource"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="exam_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
