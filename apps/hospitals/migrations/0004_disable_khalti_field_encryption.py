from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hospitals', '0003_hospital_khalti_public_key_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hospital',
            name='khalti_public_key',
            field=models.CharField(blank=True, help_text='Khalti public key for payment processing', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='hospital',
            name='khalti_secret_key',
            field=models.CharField(blank=True, help_text='Khalti secret key for payment processing', max_length=255, null=True),
        ),
    ]
