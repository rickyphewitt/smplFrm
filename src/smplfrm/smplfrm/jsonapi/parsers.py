"""JSON:API parser for smplFrm.

Accepts requests with Content-Type: application/vnd.api+json.
"""

from rest_framework.parsers import JSONParser


class JsonApiParser(JSONParser):
    """Parser that accepts application/vnd.api+json requests.

    This is a scoped parser for views that have migrated to JSON:API.
    It does not globally replace the default parser.
    """

    media_type = "application/vnd.api+json"
