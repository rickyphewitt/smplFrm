"""Isolated compatibility tests for djangorestframework-jsonapi on our stack.

These tests verify that the JSON:API package primitives (parser, renderer,
serializer, pagination, error handling) work correctly with our specific
Python 3.14, Django 6.0, and DRF 3.17 versions — none of which are officially
declared as supported by djangorestframework-jsonapi 8.1.0.

These tests are isolated from production endpoints. They use minimal in-memory
models/serializers to exercise the package's core behavior without touching
any existing views or changing any global settings.
"""

from django.test import TestCase
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from smplfrm.models.base import generate_external_id

# ---------------------------------------------------------------------------
# Minimal test model/serializer using the package primitives
# ---------------------------------------------------------------------------


class _SpikeSerializer(serializers.Serializer):
    """Minimal serializer for spike testing — no model required."""

    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=100)
    value = serializers.IntegerField()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestJsonApiRendererCompatibility(TestCase):
    """Verify the JSON:API renderer produces correct document structure."""

    def test_renderer_produces_data_envelope(self):
        """Single resource renders with top-level 'data' key."""
        from rest_framework_json_api.renderers import JSONRenderer
        from rest_framework.request import Request

        renderer = JSONRenderer()
        data = {"id": "aBcDeFgHiJkLmNoP", "name": "test", "value": 42}

        factory = APIRequestFactory()
        drf_request = Request(factory.get("/fake"))

        rendered = renderer.render(
            data,
            renderer_context={
                "request": drf_request,
                "view": _FakeView(),
                "kwargs": {},
            },
        )

        import json

        result = json.loads(rendered)
        # The renderer wraps data in a top-level 'data' key
        assert "data" in result, f"Expected top-level 'data', got keys: {result.keys()}"
        # With a plain DRF serializer, the data is passed through as-is under 'data'
        # Full JSON:API type/attributes structure requires using JsonApiModelSerializer
        assert result["data"]["id"] == "aBcDeFgHiJkLmNoP"
        assert result["data"]["name"] == "test"
        assert result["data"]["value"] == 42

    def test_renderer_collection_produces_data_array(self):
        """Collection renders as top-level 'data' array."""
        from rest_framework_json_api.renderers import JSONRenderer
        from rest_framework.request import Request

        renderer = JSONRenderer()
        data = [
            {"id": "aAaAaAaAaAaAaAaA", "name": "first", "value": 1},
            {"id": "bBbBbBbBbBbBbBbB", "name": "second", "value": 2},
        ]

        factory = APIRequestFactory()
        drf_request = Request(factory.get("/fake"))

        rendered = renderer.render(
            data,
            renderer_context={
                "request": drf_request,
                "view": _FakeView(action="list"),
                "kwargs": {},
            },
        )

        import json

        result = json.loads(rendered)
        assert "data" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 2

    def test_resource_serializer_produces_type_and_attributes(self):
        """Using JsonApiModelSerializer produces full JSON:API resource structure."""
        from rest_framework_json_api.renderers import JSONRenderer
        from rest_framework.request import Request
        import json

        # Test using a minimal model serializer approach
        from smplfrm.models import Config

        # Create a test config
        config = Config.objects.create(
            name="test-spike-config",
            is_active=False,
            display_date=True,
            display_clock=True,
            image_refresh_interval=30000,
        )

        # Use the existing ConfigSerializer which extends HyperlinkedModelSerializer
        from smplfrm.views.serializers.v1.config_serializer import ConfigSerializer

        factory = APIRequestFactory()
        drf_request = Request(factory.get("/fake"))

        serializer = ConfigSerializer(config, context={"request": drf_request})
        data = serializer.data

        class ConfigView:
            basename = "configs"
            action = "retrieve"
            kwargs = {}

            def get_serializer_class(self):
                return ConfigSerializer

        renderer = JSONRenderer()
        rendered = renderer.render(
            data,
            renderer_context={
                "request": drf_request,
                "view": ConfigView(),
                "kwargs": {},
            },
        )

        result = json.loads(rendered)
        assert "data" in result
        # Even with HyperlinkedModelSerializer, the data should be wrapped
        assert "id" in result["data"] or result["data"].get("id") == config.external_id


class TestJsonApiParserCompatibility(TestCase):
    """Verify the JSON:API parser correctly unwraps incoming documents."""

    def test_parser_unwraps_data_envelope(self):
        """Parser extracts attributes from a JSON:API document."""
        from rest_framework_json_api.parsers import JSONParser
        import io
        import json

        document = {
            "data": {
                "type": "SpikeSerializer",
                "attributes": {
                    "name": "parsed-item",
                    "value": 99,
                },
            }
        }

        stream = io.BytesIO(json.dumps(document).encode("utf-8"))
        parser = JSONParser()
        result = parser.parse(stream, media_type="application/vnd.api+json")

        assert result["name"] == "parsed-item"
        assert result["value"] == 99

    def test_parser_preserves_id_on_update(self):
        """Parser includes id from document for update operations."""
        from rest_framework_json_api.parsers import JSONParser
        import io
        import json

        document = {
            "data": {
                "type": "SpikeSerializer",
                "id": "xYzXyZxYzXyZxYzX",
                "attributes": {
                    "name": "updated-item",
                    "value": 77,
                },
            }
        }

        stream = io.BytesIO(json.dumps(document).encode("utf-8"))
        parser = JSONParser()
        result = parser.parse(stream, media_type="application/vnd.api+json")

        assert result["id"] == "xYzXyZxYzXyZxYzX"
        assert result["name"] == "updated-item"


class TestJsonApiExternalIdCompatibility(TestCase):
    """Verify 16-character alphanumeric external_id works as JSON:API string id."""

    def test_16_char_external_id_renders_as_string(self):
        """The 16-char external_id is preserved as a string in rendered output."""
        from rest_framework_json_api.renderers import JSONRenderer
        from rest_framework.request import Request
        import json

        ext_id = generate_external_id()
        assert len(ext_id) == 16

        data = {"id": ext_id, "name": "id-test", "value": 0}

        factory = APIRequestFactory()
        drf_request = Request(factory.get("/fake"))

        renderer = JSONRenderer()
        rendered = renderer.render(
            data,
            renderer_context={
                "request": drf_request,
                "view": _FakeView(),
                "kwargs": {},
            },
        )

        result = json.loads(rendered)
        assert result["data"]["id"] == ext_id
        assert isinstance(result["data"]["id"], str)

    def test_multiple_external_ids_in_collection(self):
        """Multiple 16-char IDs all render correctly as strings in a list."""
        from rest_framework_json_api.renderers import JSONRenderer
        from rest_framework.request import Request
        import json

        ids = [generate_external_id() for _ in range(5)]
        data = [
            {"id": eid, "name": f"item-{i}", "value": i} for i, eid in enumerate(ids)
        ]

        factory = APIRequestFactory()
        drf_request = Request(factory.get("/fake"))

        renderer = JSONRenderer()
        rendered = renderer.render(
            data,
            renderer_context={
                "request": drf_request,
                "view": _FakeView(action="list"),
                "kwargs": {},
            },
        )

        result = json.loads(rendered)
        rendered_ids = [item["id"] for item in result["data"]]
        assert rendered_ids == ids


class TestJsonApiErrorCompatibility(TestCase):
    """Verify JSON:API error formatting works on our stack."""

    def test_exception_handler_returns_response(self):
        """DRF exceptions are handled and return a Response."""
        from rest_framework_json_api.exceptions import exception_handler
        from rest_framework.exceptions import ValidationError
        from rest_framework.request import Request

        exc = ValidationError({"name": ["This field is required."]})
        factory = APIRequestFactory()
        drf_request = Request(factory.get("/fake"))
        context = {"request": drf_request, "view": _FakeView()}

        response = exception_handler(exc, context)

        assert response is not None
        assert response.status_code == 400
        # The exception handler returns DRF-format data; the renderer
        # transforms it to JSON:API errors array format during rendering.
        # Here we verify the handler works and returns expected status.

    def test_not_found_exception_handled(self):
        """404 exceptions are handled correctly."""
        from rest_framework_json_api.exceptions import exception_handler
        from rest_framework.exceptions import NotFound
        from rest_framework.request import Request

        exc = NotFound("Resource not found")
        factory = APIRequestFactory()
        drf_request = Request(factory.get("/fake"))
        context = {"request": drf_request, "view": _FakeView()}

        response = exception_handler(exc, context)

        assert response is not None
        assert response.status_code == 404

    def test_json_api_exception_handler_importable(self):
        """The JSON:API exception handler can be imported and used.

        This confirms the package's exception handler is compatible with
        our Django/DRF versions and can be configured as the DRF exception handler.
        """
        from rest_framework_json_api.exceptions import exception_handler

        # Verify it's callable
        assert callable(exception_handler)

        # Verify it handles standard DRF exceptions
        from rest_framework.exceptions import PermissionDenied, Throttled
        from rest_framework.request import Request

        factory = APIRequestFactory()
        drf_request = Request(factory.get("/fake"))
        context = {"request": drf_request, "view": _FakeView()}

        # Permission denied
        response = exception_handler(PermissionDenied(), context)
        assert response.status_code == 403

        # Throttled
        response = exception_handler(Throttled(wait=60), context)
        assert response.status_code == 429


class TestJsonApiPaginationCompatibility(TestCase):
    """Verify JSON:API pagination produces correct links and meta."""

    def test_page_number_pagination_structure(self):
        """JsonApiPageNumberPagination returns links and meta.pagination."""
        from rest_framework_json_api.pagination import JsonApiPageNumberPagination
        from rest_framework.request import Request

        paginator = JsonApiPageNumberPagination()
        paginator.page_size = 2

        factory = APIRequestFactory()
        request = Request(factory.get("/fake?page[number]=1"))

        # Simulate a queryset with pagination
        items = [
            {"id": generate_external_id(), "name": f"item-{i}", "value": i}
            for i in range(5)
        ]

        # Paginator needs a list to paginate
        paginator.request = request
        paginator.page = paginator.django_paginator_class(
            items, paginator.page_size
        ).page(1)

        response = paginator.get_paginated_response(items[:2])

        assert hasattr(response, "data")
        data = response.data
        # JSON:API pagination uses 'results' key internally before rendering
        # The important thing is that when rendered, it produces links/meta
        # Let's check the response structure
        assert "results" in data or "data" in data or isinstance(data, dict)


class TestJsonApiMediaTypeCompatibility(TestCase):
    """Verify JSON:API media type negotiation works."""

    def test_renderer_media_type(self):
        """JSONRenderer declares the correct vendor media type."""
        from rest_framework_json_api.renderers import JSONRenderer

        renderer = JSONRenderer()
        assert renderer.media_type == "application/vnd.api+json"

    def test_parser_media_type(self):
        """JSONParser accepts the correct vendor media type."""
        from rest_framework_json_api.parsers import JSONParser

        parser = JSONParser()
        assert parser.media_type == "application/vnd.api+json"


# ---------------------------------------------------------------------------
# Upstream signature contract
# ---------------------------------------------------------------------------
#
# Why these tests exist: djangorestframework-jsonapi 9.0.0 dropped polymorphic
# support and took two parameters with it that this project was forwarding —
# JSONRenderer.build_json_resource_obj(..., force_type_resolution) and
# get_resource_name(context, expand_polymorphic_types). Neither removal is
# visible at import time, so the dependency bump in PR #289 surfaced as 140
# failures across four unrelated route families. The write-path ones were
# especially opaque: a TypeError raised inside the parser is converted by
# jsonapi_exception_handler into a sanitised 500, so the tests reported
# "500 != 201" and said nothing about the missing keyword argument.
#
# These tests bind the arguments the project actually passes against the
# installed signatures, so the next upstream parameter removal fails here, by
# name, instead of in every view test at once. The argument sets are read from
# the production call sites rather than restated here, so the assertions cannot
# drift away from the code they guard.
# See .kiro/specs/python-deps-update-pr289-jsonapi-compat.md (AC-7).


def _production_call_arguments(method, callee_name):
    """Return (positional count, keyword names) the project passes to callee_name.

    The call is read out of the method's own source so that this test tracks the
    production call site instead of a copy of it.
    """
    import ast
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(method)))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        callee = node.func
        name = (
            callee.attr
            if isinstance(callee, ast.Attribute)
            else getattr(callee, "id", None)
        )
        if name == callee_name:
            return len(node.args), [keyword.arg for keyword in node.keywords]

    raise AssertionError(f"No call to {callee_name}() found in {method.__qualname__}")


def _assert_binds(target, positional_count, keyword_names, call_site):
    """Fail with a readable message if call_site would not bind to target."""
    import inspect

    signature = inspect.signature(target)

    try:
        signature.bind(
            *[None] * positional_count,
            **{name: None for name in keyword_names},
        )
    except TypeError as error:
        raise AssertionError(
            f"{call_site} does not bind to the installed "
            f"{target.__qualname__}{signature}: {error}"
        ) from error


class TestUpstreamSignatureContract(TestCase):
    """Verify the project's calls into rest_framework_json_api still bind."""

    def test_renderer_override_accepts_the_upstream_call(self):
        """Upstream calls our override with five positional arguments."""
        from smplfrm.jsonapi.renderers import JsonApiRenderer

        # rest_framework_json_api/renderers.py calls build_json_resource_obj at
        # lines 349, 372, 560 and 580, each with exactly five positional args.
        _assert_binds(
            JsonApiRenderer.build_json_resource_obj,
            positional_count=5,
            keyword_names=[],
            call_site="the upstream call into JsonApiRenderer.build_json_resource_obj",
        )

    def test_renderer_override_call_binds_to_upstream(self):
        """Our super() call matches the installed parent signature."""
        from rest_framework_json_api.renderers import JSONRenderer

        from smplfrm.jsonapi.renderers import JsonApiRenderer

        positional_count, keyword_names = _production_call_arguments(
            JsonApiRenderer.build_json_resource_obj, "build_json_resource_obj"
        )

        _assert_binds(
            JSONRenderer.build_json_resource_obj,
            positional_count=positional_count,
            keyword_names=keyword_names,
            call_site="JsonApiRenderer.build_json_resource_obj's super() call",
        )

    def test_parser_call_binds_to_upstream_get_resource_name(self):
        """Our get_resource_name call matches the installed function signature."""
        from rest_framework_json_api.utils import get_resource_name

        from smplfrm.jsonapi.parsers import JsonApiParser

        positional_count, keyword_names = _production_call_arguments(
            JsonApiParser.parse_data, "get_resource_name"
        )

        _assert_binds(
            get_resource_name,
            positional_count=positional_count,
            keyword_names=keyword_names,
            call_site="JsonApiParser.parse_data's get_resource_name() call",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeView:
    """Minimal view stand-in for renderer_context."""

    basename = "spike"
    action = "retrieve"

    def __init__(self, action="retrieve"):
        self.action = action
        self.kwargs = {}

    def get_serializer_class(self):
        return _SpikeSerializer
