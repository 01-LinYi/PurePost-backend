# Generated by Django 5.2 on 2025-04-04 02:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content_moderation', '0005_post_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('published', 'Published')], default='published', max_length=10),
        ),
    ]
