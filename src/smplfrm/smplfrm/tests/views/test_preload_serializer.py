"""Tests for preload task serializer validation."""

from django.test import TestCase

from smplfrm.views.serializers.v1.preload_serializer import (
    PreloadImageCacheTaskSerializer,
)


class TestPreloadImageCacheTaskSerializer(TestCase):
    """Test suite for PreloadImageCacheTaskSerializer validation."""

    def test_valid_preload_payload(self):
        """Test that a valid preload payload passes validation."""
        data = {
            "image_ids": ["abc123", "def456", "ghi789"],
            "width": 1920,
            "height": 1080,
        }
        serializer = PreloadImageCacheTaskSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            serializer.validated_data["image_ids"], ["abc123", "def456", "ghi789"]
        )
        self.assertEqual(serializer.validated_data["width"], 1920)
        self.assertEqual(serializer.validated_data["height"], 1080)

    def test_dimensions_1_to_4096_accepted(self):
        """Test that dimensions from 1 to 4096 are accepted."""
        for dim in [1, 100, 1920, 4096]:
            with self.subTest(dim=dim):
                data = {
                    "image_ids": ["abc123"],
                    "width": dim,
                    "height": dim,
                }
                serializer = PreloadImageCacheTaskSerializer(data=data)
                self.assertTrue(
                    serializer.is_valid(), f"Dimension {dim} should be valid"
                )

    def test_dimensions_zero_rejected(self):
        """Test that zero dimensions are rejected."""
        data = {
            "image_ids": ["abc123"],
            "width": 0,
            "height": 1080,
        }
        serializer = PreloadImageCacheTaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("width", serializer.errors)

    def test_dimensions_4097_rejected(self):
        """Test that dimensions exceeding 4096 are rejected."""
        data = {
            "image_ids": ["abc123"],
            "width": 4097,
            "height": 1080,
        }
        serializer = PreloadImageCacheTaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("width", serializer.errors)

    def test_dimensions_negative_rejected(self):
        """Test that negative dimensions are rejected."""
        data = {
            "image_ids": ["abc123"],
            "width": -100,
            "height": 1080,
        }
        serializer = PreloadImageCacheTaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("width", serializer.errors)

    def test_dimensions_nonnumeric_rejected(self):
        """Test that non-numeric dimensions are rejected."""
        data = {
            "image_ids": ["abc123"],
            "width": "not a number",
            "height": 1080,
        }
        serializer = PreloadImageCacheTaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("width", serializer.errors)

    def test_batch_size_6_rejected(self):
        """Test that batch size exceeding 5 is rejected."""
        data = {
            "image_ids": ["id1", "id2", "id3", "id4", "id5", "id6"],
            "width": 1920,
            "height": 1080,
        }
        serializer = PreloadImageCacheTaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("image_ids", serializer.errors)

    def test_duplicate_ids_deduplicated(self):
        """Test that duplicate image IDs are deduplicated."""
        data = {
            "image_ids": ["abc123", "def456", "abc123", "ghi789"],
            "width": 1920,
            "height": 1080,
        }
        serializer = PreloadImageCacheTaskSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        # Should have deduplicated to 3 unique IDs
        validated_ids = serializer.validated_data["image_ids"]
        self.assertEqual(len(validated_ids), 3)
        self.assertEqual(len(set(validated_ids)), 3)

    def test_empty_image_ids_rejected(self):
        """Test that empty image_ids list is rejected."""
        data = {
            "image_ids": [],
            "width": 1920,
            "height": 1080,
        }
        serializer = PreloadImageCacheTaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("image_ids", serializer.errors)

    def test_missing_required_fields_rejected(self):
        """Test that missing required fields are rejected."""
        # Missing image_ids
        serializer = PreloadImageCacheTaskSerializer(
            data={"width": 1920, "height": 1080}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("image_ids", serializer.errors)

        # Missing width
        serializer = PreloadImageCacheTaskSerializer(
            data={"image_ids": ["abc"], "height": 1080}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("width", serializer.errors)

        # Missing height
        serializer = PreloadImageCacheTaskSerializer(
            data={"image_ids": ["abc"], "width": 1920}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("height", serializer.errors)
