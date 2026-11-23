"""Library filter rule API views.

Rules are polymorphic: each rule type has its own JSON:API type
(``tag_library_filter_rules``) and serializer. The type is fixed when the
rule is created.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from smplfrm.jsonapi import jsonapi_exception_handler, StrictQueryMixin
from smplfrm.models import LibraryFilterRule
from smplfrm.services import LibraryFilterRuleService
from smplfrm.services.library_filter.exceptions import (
    LibraryFilterError,
    TypeMismatch,
    UnknownRuleType,
)
from smplfrm.services.library_filter.rule_handlers import (
    JSONAPI_TYPE_TO_RULE_TYPE,
    RULE_TYPE_TO_JSONAPI_TYPE,
)
from smplfrm.views.api.v1.library_filter_errors import to_api_error
from smplfrm.views.serializers.v1.library_filter_rules import RULE_SERIALIZERS


class LibraryFilterRuleViewSet(
    StrictQueryMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """JSON:API library filter rule endpoint.

    Supports:
    - GET /library_filter_rules - list live rules (paginated, creation order)
    - GET /library_filter_rules?filter[library_filter]={id}&filter[rule_type]=tag
    - GET /library_filter_rules/{external_id} - detail
    - POST /library_filter_rules - create; data.type selects the rule type
    - PUT /library_filter_rules/{external_id} - full replacement; the type
      and parent filter cannot change, the tag can
    - DELETE /library_filter_rules/{external_id} - soft delete; deleting the
      last rule of the active filter deactivates it

    PATCH is not routed and answers 405.

    The view checks data.type itself (defer_type_validation) so an unknown or
    changed type answers 400 unknown_rule_type / type_mismatch rather than the
    parser's generic 409.

    Security:
    - Returns 403 for unknown or deleted rule ids, and for an unknown or
      deleted parent filter, to prevent enumeration
    """

    lookup_field = "external_id"
    resource_name = "library_filter_rules"
    defer_type_validation = True
    allowed_query_params = {"page[number]"}
    allowed_filters = {"library_filter", "rule_type"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = LibraryFilterRuleService()
        self._rule_type = LibraryFilterRule.RuleType.TAG.value

    def get_exception_handler(self):
        return jsonapi_exception_handler

    def get_serializer_class(self):
        return RULE_SERIALIZERS[self._rule_type]

    def get_queryset(self):
        params = self.request.query_params
        return self.service.list_for_api(
            library_filter_id=params.get("filter[library_filter]"),
            rule_type=params.get("filter[rule_type]"),
        )

    def get_object(self):
        """Return 403 instead of 404 to prevent resource enumeration."""
        try:
            rule = super().get_object()
        except Http404:
            raise PermissionDenied("Access denied")
        self._rule_type = rule.rule_type
        return rule

    def retrieve(self, request, *args, **kwargs):
        rule = self.get_object()
        return Response(self.get_serializer(rule).data)

    def create(self, request, *args, **kwargs):
        rule_type = JSONAPI_TYPE_TO_RULE_TYPE.get(request.data.get("type"))
        if rule_type is None:
            raise to_api_error(UnknownRuleType())
        self._rule_type = rule_type
        data = self.get_serializer_class().to_service_data(request.data)
        try:
            rule = self.service.create({"rule_type": rule_type, **data})
        except LibraryFilterError as e:
            raise to_api_error(e) from e
        return Response(self.get_serializer(rule).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        rule = self.get_object()
        if request.data.get("type") != RULE_TYPE_TO_JSONAPI_TYPE[rule.rule_type]:
            raise to_api_error(TypeMismatch())
        data = self.get_serializer_class().to_service_data(request.data)
        try:
            updated = self.service.replace(rule, data)
        except LibraryFilterError as e:
            raise to_api_error(e) from e
        return Response(self.get_serializer(updated).data)

    def destroy(self, request, *args, **kwargs):
        rule = self.get_object()
        self.service.delete(rule.external_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
