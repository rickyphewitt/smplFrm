from rest_framework import serializers

from smplfrm.models import Plugin


class PluginSerializer(serializers.HyperlinkedModelSerializer):

    id = serializers.CharField(source="external_id", read_only=True)

    class Meta:
        model = Plugin
        fields = [
            "id",
            "name",
            "description",
            "settings",
        ]
        read_only_fields = ["name", "description"]
