from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medical_report', '0003_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='medicalreport',
            name='report_file',
            field=models.FileField(help_text='Uploaded medical report file', upload_to='medical_reports/'),
        ),
    ]
