"""Tag and library filter code follows the project's layer conventions."""

from django.test import SimpleTestCase
from rest_framework import serializers as drf_serializers

from smplfrm.jsonapi import jsonapi_exception_handler
from smplfrm.models import (
    ImageTag,
    LibraryFilter,
    LibraryFilterRule,
    LibraryFilterSettings,
    Tag,
)
from smplfrm.models.base import ModelBase
from smplfrm.services import (
    ImageTagService,
    LibraryFilterRuleService,
    LibraryFilterService,
    LibraryFilterSettingsService,
    TagService,
)
from smplfrm.services.base_service import BaseService
from smplfrm.services.library_filter.rule_handlers import RULE_TYPE_HANDLERS
from smplfrm.views.api.v1.library_filter_rules import LibraryFilterRuleViewSet
from smplfrm.views.api.v1.library_filter_settings import LibraryFilterSettingsViewSet
from smplfrm.views.api.v1.library_filters import LibraryFilterViewSet
from smplfrm.views.api.v1.tags import TagViewSet
from smplfrm.views.serializers.v1.library_filter_rules import RULE_SERIALIZERS
from smplfrm.views.serializers.v1.library_filter_serializer import (
    LibraryFilterSerializer,
)
from smplfrm.views.serializers.v1.library_filter_settings_serializer import (
    LibraryFilterSettingsSerializer,
)
from smplfrm.views.serializers.v1.tag_serializer import TagSerializer

MODELS = [Tag, ImageTag, LibraryFilter, LibraryFilterRule, LibraryFilterSettings]
SERVICES = [
    TagService,
    ImageTagService,
    LibraryFilterService,
    LibraryFilterRuleService,
    LibraryFilterSettingsService,
]
SERIALIZERS = [
    TagSerializer,
    LibraryFilterSerializer,
    LibraryFilterSettingsSerializer,
    *RULE_SERIALIZERS.values(),
]
VIEWSETS = [
    TagViewSet,
    LibraryFilterViewSet,
    LibraryFilterRuleViewSet,
    LibraryFilterSettingsViewSet,
]


class TestPatternConformance(SimpleTestCase):
    def test_models_inherit_model_base(self):
        for model in MODELS:
            with self.subTest(model=model.__name__):
                self.assertTrue(issubclass(model, ModelBase))

    def test_services_implement_base_service(self):
        for service in SERVICES:
            with self.subTest(service=service.__name__):
                self.assertTrue(issubclass(service, BaseService))
                self.assertEqual(service.__abstractmethods__, frozenset())

    def test_serializers_expose_external_id_as_id(self):
        for serializer_class in SERIALIZERS:
            with self.subTest(serializer=serializer_class.__name__):
                field = serializer_class().fields["id"]
                self.assertIsInstance(field, drf_serializers.CharField)
                self.assertEqual(field.source, "external_id")
                self.assertTrue(field.read_only)

    def test_viewsets_follow_api_conventions(self):
        for viewset in VIEWSETS:
            with self.subTest(viewset=viewset.__name__):
                self.assertIs(
                    viewset().get_exception_handler(), jsonapi_exception_handler
                )
                self.assertEqual(viewset.lookup_field, "external_id")
                self.assertIn(
                    "get_object",
                    vars(viewset),
                    "Detail lookups must turn 404 into 403",
                )

    def test_rule_handlers_are_a_registry_keyed_by_rule_type(self):
        self.assertIsInstance(RULE_TYPE_HANDLERS, dict)
        for rule_type, handler in RULE_TYPE_HANDLERS.items():
            with self.subTest(rule_type=rule_type):
                self.assertEqual(handler.rule_type, rule_type)
                self.assertTrue(callable(handler.to_q))
