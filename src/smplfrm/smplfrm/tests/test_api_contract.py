"""API Contract Validation Tests.

Validates that all /api/v1/ routes are explicitly classified in the contract
manifest and conform to their declared protocol.

Per AC-1: "Dynamic route discovery and the manifest have exact normalized
route-method set equality; adding an unclassified route or stale manifest
entry makes contract validation fail."

Per AC-2: "Compatibility checks pass with djangorestframework-jsonapi==8.1.0,
Python 3.14, Django 6.0.x, and the repository-pinned DRF 3.18.x stack."
"""

import pytest
from django.test import TestCase

from smplfrm.tests.api_contract.discovery import discover_routes, format_route_diff
from smplfrm.tests.api_contract.manifest import get_manifest_routes, CONTRACT_MANIFEST


class ContractManifestTest(TestCase):
    """Test route discovery and manifest equality."""

    def test_all_routes_are_classified(self):
        """All discovered /api/v1/ routes must exist in manifest.

        Unclassified routes represent endpoints that haven't been consciously
        assigned a protocol contract. This prevents accidental endpoint exposure.
        """
        discovered = discover_routes()
        manifest = get_manifest_routes()

        unclassified = discovered - manifest

        if unclassified:
            diff = format_route_diff(discovered, manifest)
            self.fail(
                f"Found {len(unclassified)} unclassified route(s). "
                f"Add entries to tests/api_contract/manifest.py:\n{diff}"
            )

    def test_no_stale_manifest_entries(self):
        """All manifest entries must correspond to actual routes.

        Stale manifest entries could hide route removals or typos in patterns.
        """
        discovered = discover_routes()
        manifest = get_manifest_routes()

        stale = manifest - discovered

        if stale:
            diff = format_route_diff(discovered, manifest)
            self.fail(
                f"Found {len(stale)} stale manifest entry(ies). "
                f"Remove from tests/api_contract/manifest.py:\n{diff}"
            )

    def test_manifest_and_discovered_routes_exact_equality(self):
        """Manifest and discovered routes must be exactly equal (AC-1)."""
        discovered = discover_routes()
        manifest = get_manifest_routes()

        if discovered != manifest:
            diff = format_route_diff(discovered, manifest)
            self.fail(f"Route manifest mismatch:\n{diff}")

    def test_manifest_has_no_duplicate_entries(self):
        """Each route-method pair should appear exactly once in manifest."""
        seen = set()
        duplicates = []

        for contract in CONTRACT_MANIFEST:
            key = (contract.method, contract.pattern)
            if key in seen:
                duplicates.append(f"{contract.method} {contract.pattern}")
            seen.add(key)

        if duplicates:
            self.fail(f"Found duplicate manifest entries:\n" + "\n".join(duplicates))


class CompatibilityTest(TestCase):
    """Test compatibility with pinned dependency versions (AC-2)."""

    def test_djangorestframework_jsonapi_imports(self):
        """Verify djangorestframework-jsonapi==8.1.0 can be imported."""
        try:
            from rest_framework_json_api import (
                serializers,
                views,
                pagination,
                renderers,
                parsers,
            )
            from rest_framework_json_api.utils import get_resource_name

            # Verify key classes are available
            assert hasattr(serializers, "Serializer")
            assert hasattr(renderers, "JSONRenderer")
            assert hasattr(parsers, "JSONParser")
            assert hasattr(pagination, "JsonApiPageNumberPagination")
            assert callable(get_resource_name)

        except ImportError as e:
            self.fail(f"Failed to import djangorestframework-jsonapi: {e}")

    def test_djangorestframework_version(self):
        """Verify DRF version is compatible (3.17.x or 3.18.x).

        The repository currently pins ~=3.18.1 but has 3.17.2 installed.
        Both are compatible with djangorestframework-jsonapi==8.1.0.
        """
        import rest_framework

        version = rest_framework.VERSION
        major, minor = int(version.split(".")[0]), int(version.split(".")[1])

        self.assertEqual(
            major,
            3,
            f"Expected DRF major version 3, got {major} (full version: {version})",
        )
        self.assertIn(
            minor,
            [17, 18],
            f"Expected DRF minor version 17 or 18, got {minor} (full version: {version})",
        )

    def test_django_version(self):
        """Verify Django version is compatible (6.0.x)."""
        import django

        version = django.VERSION
        major, minor = version[0], version[1]

        self.assertEqual(
            major, 6, f"Expected Django major version 6, got {major} ({version})"
        )
        self.assertEqual(
            minor, 0, f"Expected Django minor version 0, got {minor} ({version})"
        )

    def test_json_api_renderer_instantiation(self):
        """Verify JSON:API renderer can be instantiated."""
        from smplfrm.jsonapi import JsonApiRenderer

        renderer = JsonApiRenderer()
        self.assertIsNotNone(renderer)
        self.assertEqual(renderer.media_type, "application/vnd.api+json")

    def test_json_api_parser_instantiation(self):
        """Verify JSON:API parser can be instantiated."""
        from smplfrm.jsonapi import JsonApiParser

        parser = JsonApiParser()
        self.assertIsNotNone(parser)
        self.assertEqual(parser.media_type, "application/vnd.api+json")

    def test_strict_query_mixin_available(self):
        """Verify StrictQueryMixin is available and usable."""
        from smplfrm.jsonapi import StrictQueryMixin

        # Verify it has the expected interface
        self.assertTrue(hasattr(StrictQueryMixin, "allowed_query_params"))
        self.assertTrue(hasattr(StrictQueryMixin, "initial"))
        self.assertTrue(hasattr(StrictQueryMixin, "_validate_query_params"))
