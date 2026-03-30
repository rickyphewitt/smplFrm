from rest_framework import serializers

from smplfrm.models import Plugin
from smplfrm.plugins import PLUGIN_REGISTRY


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
