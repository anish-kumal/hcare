from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('patients', '0006_patient_booking_code_autogenerate'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppointmentPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='modified')),
                ('is_active', models.BooleanField(default=True)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Amount to collect', max_digits=10)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PAID', 'Paid'), ('FAILED', 'Failed'), ('REFUNDED', 'Refunded')], default='PENDING', help_text='Payment status', max_length=20)),
                ('payment_method', models.CharField(choices=[('CASH', 'Cash'), ('CARD', 'Card'), ('ONLINE', 'Online'), ('INSURANCE', 'Insurance')], default='CASH', help_text='Payment mode used by patient', max_length=20)),
                ('transaction_reference', models.CharField(blank=True, max_length=100, null=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('appointment', models.OneToOneField(help_text='Appointment linked to this payment', on_delete=django.db.models.deletion.CASCADE, related_name='payment', to='patients.patientappointment')),
            ],
            options={
                'verbose_name': 'Appointment Payment',
                'verbose_name_plural': 'Appointment Payments',
                'ordering': ['-created'],
            },
        ),
        migrations.AddIndex(
            model_name='appointmentpayment',
            index=models.Index(fields=['status'], name='payments_app_status_0af64f_idx'),
        ),
        migrations.AddIndex(
            model_name='appointmentpayment',
            index=models.Index(fields=['payment_method'], name='payments_app_payment_360d68_idx'),
        ),
    ]
