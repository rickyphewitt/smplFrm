from rest_framework import serializers

from smplfrm.models import ImageMetadata


class ImageMetadataSerializer(serializers.HyperlinkedModelSerializer):

    id = serializers.CharField(source="external_id")
    taken = serializers.DateTimeField()

    class Meta:
        model = ImageMetadata
        fields = ["id", "taken", "created", "updated"]
