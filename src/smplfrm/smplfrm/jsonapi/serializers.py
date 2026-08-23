"""JSON:API serializers for smplFrm.

Serializers define the structure of JSON:API resources.
Uses rest_framework_json_api for proper JSON:API document structure.
"""

from rest_framework_json_api import serializers


class WeatherSerializer(serializers.Serializer):
    """Serializer for weather singleton resource.

    The resource_name in Meta sets the JSON:API type to "weather".
    The id field defaults to "current" for the singleton resource.
    """

    id = serializers.CharField(read_only=True, default="current")
    temperature = serializers.CharField()
    temperature_scale = serializers.CharField()
    daily_low = serializers.CharField()
    daily_low_scale = serializers.CharField()
    daily_high = serializers.CharField()
    daily_high_scale = serializers.CharField()

    class Meta:
        resource_name = "weather"
