from rest_framework import serializers

from smplfrm.models import Plugin
from smplfrm.plugins import PLUGIN_REGISTRY

SECRET_MASK = "******"


class PluginSerializer(serializers.HyperlinkedModelSerializer):

    id = serializers.CharField(source="external_id", read_only=True)
    settings_schema = serializers.SerializerMethodField()

    class Meta:
        model = Plugin
        fields = [
            "id",
            "name",
            "description",
            "settings",
            "settings_schema",
        ]
        read_only_fields = ["name", "description"]

    def get_settings_schema(self, obj):
        for cls in PLUGIN_REGISTRY:
            plugin = cls()
            if plugin.name == obj.name:
                return plugin.get_settings_schema()
        return []

    def _get_secret_keys(self, plugin_name):
        """Return set of setting keys marked as type 'password' for a plugin."""
        for cls in PLUGIN_REGISTRY:
            plugin = cls()
            if plugin.name == plugin_name:
                return {
                    field["key"]
                    for field in plugin.get_settings_schema()
                    if field.get("type") == "password"
                }
        return set()

    def to_representation(self, instance):
        """Mask secret fields in the serialized output."""
        data = super().to_representation(instance)
        secret_keys = self._get_secret_keys(instance.name)
        if secret_keys and data.get("settings"):
            masked_settings = dict(data["settings"])
            for key in secret_keys:
                if key in masked_settings:
                    masked_settings[key] = SECRET_MASK
            data["settings"] = masked_settings
        return data
