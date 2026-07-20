# Generated migration for adding amount field to Booking model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('movies', '0006_auto_20260701_1349'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text='Booking amount in currency units', max_digits=8),
        ),
    ]
