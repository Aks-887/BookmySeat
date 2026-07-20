from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('movies', '0008_payment_gateway_hardening'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='seat',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to='movies.seat'),
        ),
        migrations.AlterField(
            model_name='seatreservation',
            name='seat',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservations', to='movies.seat'),
        ),
    ]
