# Generated by Django 5.1.7 on 2025-03-22 09:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='problemcard',
            name='analysis',
            field=models.TextField(blank=True),
        ),
    ]
