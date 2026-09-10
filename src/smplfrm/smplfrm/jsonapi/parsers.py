"""JSON:API parser for smplFrm.

Accepts requests with Content-Type: application/vnd.api+json.
Uses rest_framework_json_api parser to properly unwrap JSON:API documents.
"""

from rest_framework_json_api.parsers import JSONParser as JsonApiPackageParser
from rest_framework_json_api import exceptions
from rest_framework_json_api.utils import get_resource_name


class JsonApiParser(JsonApiPackageParser):
    """Parser that accepts and unwraps application/vnd.api+json requests.

    Extends the package's parser which extracts attributes from the
    JSON:API document structure for use by serializers.

    Supports polymorphic types by checking if the view's serializer has
    a get_accepted_types method.
    """

    def parse_data(self, result, parser_context):
        """Override to support polymorphic types.

        If the view's serializer defines get_accepted_types(), those types
        are accepted in addition to the default resource name.
        """
        if not isinstance(result, dict) or "data" not in result:
            from rest_framework.exceptions import ParseError

            raise ParseError("Received document does not contain primary data")

        data = result.get("data")
        parser_context = parser_context or {}
        view = parser_context.get("view")
        request = parser_context.get("request")
        method = request and request.method

        # Sanity check
        if not isinstance(data, dict):
            from rest_framework.exceptions import ParseError

            raise ParseError(
                "Received data is not a valid JSON:API Resource Identifier Object"
            )

        # Check for inconsistencies with polymorphic support
        if method in ("PUT", "POST", "PATCH"):
            resource_name = get_resource_name(
                parser_context, expand_polymorphic_types=True
            )

            # Get accepted types from serializer if available
            accepted_types = self._get_accepted_types(view, resource_name)

            data_type = data.get("type")
            if isinstance(accepted_types, str):
                if data_type != accepted_types:
                    raise exceptions.Conflict(
                        f"The resource object's type ({data_type}) is not the type "
                        f"that constitute the collection represented by the endpoint "
                        f"({accepted_types})."
                    )
            elif isinstance(accepted_types, (list, tuple, set)):
                if data_type not in accepted_types:
                    raise exceptions.Conflict(
                        f"The resource object's type ({data_type}) is not the type "
                        f"that constitute the collection represented by the endpoint "
                        f"(one of [{', '.join(accepted_types)}])."
                    )

        # ID validation for PUT/PATCH
        if not data.get("id") and method in ("PATCH", "PUT"):
            from rest_framework.exceptions import ParseError

            raise ParseError(
                "The resource identifier object must contain an 'id' member"
            )

        if method in ("PATCH", "PUT"):
            lookup_url_kwarg = getattr(view, "lookup_url_kwarg", None) or getattr(
                view, "lookup_field", None
            )
            if lookup_url_kwarg and str(data.get("id")) != str(
                view.kwargs[lookup_url_kwarg]
            ):
                raise exceptions.Conflict(
                    f"The resource object's id ({data.get('id')}) does not match "
                    f"url's lookup id ({view.kwargs[lookup_url_kwarg]})."
                )

        # Construct the return data
        parsed_data = {"id": data.get("id")} if "id" in data else {}
        parsed_data["type"] = data.get("type")
        parsed_data.update(self.parse_attributes(data))
        parsed_data.update(self.parse_relationships(data))
        parsed_data.update(self.parse_metadata(result))
        return parsed_data

    def _get_accepted_types(self, view, default_resource_name):
        """Get accepted types from view's serializer or return default."""
        if not view:
            return default_resource_name

        try:
            serializer_class = view.get_serializer_class()
            if hasattr(serializer_class, "get_accepted_types"):
                return serializer_class.get_accepted_types()
        except AttributeError:
            pass

        return default_resource_name
