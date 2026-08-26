"""JSON:API parser for smplFrm.

Accepts requests with Content-Type: application/vnd.api+json.
Uses rest_framework_json_api parser to properly unwrap JSON:API documents.
"""

from rest_framework_json_api.parsers import JSONParser as JsonApiPackageParser


class JsonApiParser(JsonApiPackageParser):
    """Parser that accepts and unwraps application/vnd.api+json requests.

    Extends the package's parser which extracts attributes from the
    JSON:API document structure for use by serializers.
    """

    pass
