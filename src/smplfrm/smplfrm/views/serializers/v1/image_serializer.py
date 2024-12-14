from rest_framework import serializers

from smplfrm.models import Image


class ImageSerializer(serializers.HyperlinkedModelSerializer):

    id = serializers.CharField(source="external_id")

    class Meta:
        model = Image
        fields = ["id", "name", "file_path", "file_name", "created", "updated"]