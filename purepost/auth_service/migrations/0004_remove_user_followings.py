# Generated by Django 5.1.6 on 2025-04-14 21:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth_service', '0003_user_is_verified'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='followings',
        ),
    ]
