# Generated by Django 4.2.17 on 2025-01-03 02:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smplfrm', '0003_rename_created_date_image_created_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='view_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
