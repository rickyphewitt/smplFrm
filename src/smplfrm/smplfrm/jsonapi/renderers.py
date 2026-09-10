"""JSON:API renderer for smplFrm.

Extends the package's JSONRenderer to handle error responses correctly
when using a custom exception handler, and supports dynamic resource types.
"""

from rest_framework_json_api.renderers import JSONRenderer as PackageJSONRenderer
from rest_framework_json_api.utils import get_resource_id


class JsonApiRenderer(PackageJSONRenderer):
    """JSON:API renderer that handles custom exception handler output.

    The package's renderer expects errors to come from DRF's exception
    handling flow. When using a custom exception handler that returns
    pre-formatted JSON:API errors, we need to pass them through unchanged.

    Also supports dynamic resource types via get_resource_type_from_instance
    method on serializers.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """Render data, passing through pre-formatted error responses."""
        # If data already has 'errors' key, it's from our exception handler
        # Pass it through without the package's document wrapping
        if isinstance(data, dict) and "errors" in data:
            from rest_framework.renderers import JSONRenderer

            return JSONRenderer.render(
                self, data, accepted_media_type, renderer_context
            )

        # Normal success response - let package handle document structure
        return super().render(data, accepted_media_type, renderer_context)

    @classmethod
    def build_json_resource_obj(
        cls,
        fields,
        resource,
        resource_instance,
        resource_name,
        serializer,
        force_type_resolution=False,
    ):
        """Build resource object with support for dynamic types.

        If the serializer has a get_resource_type_from_instance classmethod,
        use it to determine the type dynamically.
        """
        # Check for dynamic type method on serializer
        serializer_class = serializer.__class__
        if hasattr(serializer, "child"):
            serializer_class = serializer.child.__class__

        if hasattr(serializer_class, "get_resource_type_from_instance"):
            resource_name = serializer_class.get_resource_type_from_instance(
                resource_instance
            )

        return super().build_json_resource_obj(
            fields,
            resource,
            resource_instance,
            resource_name,
            serializer,
            force_type_resolution=False,  # We handled it
        )
