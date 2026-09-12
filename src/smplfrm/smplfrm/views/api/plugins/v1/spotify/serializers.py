"""JSON:API serializers for Spotify plugin resources."""

import hashlib

from rest_framework import serializers


def generate_track_id(uri):
    """Generate an opaque track ID from Spotify URI.

    Args:
        uri: Spotify URI (e.g., 'spotify:track:abc123')

    Returns:
        16-character hex string, or None if uri is None
    """
    if not uri:
        return None
    return hashlib.sha256(uri.encode()).hexdigest()[:16]


class SpotifyTrackSerializer(serializers.Serializer):
    """Serializer for spotify_tracks resource.

    Represents a currently playing track with opaque ID derived from Spotify URI.
    """

    id = serializers.SerializerMethodField()
    artist = serializers.CharField()
    song = serializers.CharField()

    class Meta:
        resource_name = "spotify_tracks"

    def get_id(self, obj):
        """Generate opaque ID from track URI."""
        return generate_track_id(obj.get("uri"))

    def to_representation(self, instance):
        """Format as JSON:API resource object."""
        track_id = self.get_id(instance)
        if not track_id:
            return None

        return {
            "type": "spotify_tracks",
            "id": track_id,
            "attributes": {
                "artist": instance.get("artist"),
                "song": instance.get("song"),
            },
        }


class SpotifyStatusSerializer(serializers.Serializer):
    """Serializer for spotify_status singleton resource.

    Represents current Spotify playback status with optional track relationship.
    """

    id = serializers.CharField(default="current", read_only=True)
    is_playing = serializers.BooleanField()
    track = SpotifyTrackSerializer(required=False, allow_null=True)

    class Meta:
        resource_name = "spotify_status"

    def to_representation(self, instance):
        """Format as JSON:API document with included track."""
        track_data = instance.get("track")
        track_serializer = SpotifyTrackSerializer()
        track_resource = (
            track_serializer.to_representation(track_data) if track_data else None
        )

        # Build relationship data
        relationship_data = None
        if track_resource:
            relationship_data = {
                "type": track_resource["type"],
                "id": track_resource["id"],
            }

        response = {
            "data": {
                "type": "spotify_status",
                "id": "current",
                "attributes": {
                    "is_playing": instance.get("is_playing", False),
                },
                "relationships": {
                    "track": {
                        "data": relationship_data,
                    },
                },
            },
        }

        # Include track in included array if present
        if track_resource:
            response["included"] = [track_resource]

        return response
