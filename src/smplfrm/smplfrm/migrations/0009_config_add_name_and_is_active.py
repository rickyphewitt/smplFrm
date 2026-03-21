from django.db import migrations, models


def set_existing_config_defaults(apps, schema_editor):
    Config = apps.get_model("smplfrm", "Config")
    Config.objects.filter(name="").update(name="smplFrm Default", is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ("smplfrm", "0008_config_image_cache_timeout"),
    ]

    operations = [
        migrations.AddField(
            model_name="config",
            name="name",
            field=models.CharField(default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="config",
            name="is_active",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(set_existing_config_defaults, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="config",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True),
                fields=("is_active",),
                name="unique_active_config",
            ),
        ),
        migrations.AlterField(
            model_name="config",
            name="name",
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
