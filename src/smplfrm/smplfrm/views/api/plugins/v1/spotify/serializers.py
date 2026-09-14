"""JSON:API serializers for Spotify plugin resources."""

import hashlib

from rest_framework import serializers


def generate_track_id(track_data):
    """Generate an opaque track ID from Spotify track data.

    For tracks with URIs, uses the URI.
    For podcasts/episodes without URIs, uses artist+song combination.

    Args:
        track_data: dict with 'uri', 'artist', and 'song' keys

    Returns:
        16-character hex string, or None if track_data is None
    """
    if not track_data:
        return None

    uri = track_data.get("uri")

    if uri:
        # Standard track with URI
        return hashlib.sha256(uri.encode()).hexdigest()[:16]

    # Podcast or other content without URI - use artist+song
    artist = track_data.get("artist", "")
    song = track_data.get("song", "")

    if artist or song:
        content = f"{artist}:{song}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    return None


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
        """Generate opaque ID from track data."""
        return generate_track_id(obj)

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
