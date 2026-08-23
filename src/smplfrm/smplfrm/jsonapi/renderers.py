"""JSON:API renderer for smplFrm.

Extends the package's JSONRenderer to handle error responses correctly
when using a custom exception handler.
"""

from rest_framework_json_api.renderers import JSONRenderer as PackageJSONRenderer


class JsonApiRenderer(PackageJSONRenderer):
    """JSON:API renderer that handles custom exception handler output.

    The package's renderer expects errors to come from DRF's exception
    handling flow. When using a custom exception handler that returns
    pre-formatted JSON:API errors, we need to pass them through unchanged.

    This can be removed when JSON_API_UNIFORM_EXCEPTIONS is enabled globally.
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
