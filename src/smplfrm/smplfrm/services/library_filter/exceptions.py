"""Domain errors raised by the library filter services.

Each error carries a stable ``code`` and a client-safe ``detail``; views turn
them into JSON:API error responses.
"""


class LibraryFilterError(Exception):
    """Base class for library filter domain errors."""

    code = "library_filter_error"
    default_detail = "The library filter request is invalid"

    def __init__(self, detail: str = None):
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class LibraryFilterNotFound(LibraryFilterError):
    code = "library_filter_not_found"
    default_detail = "Library filter not found"


class LibraryFilterRequired(LibraryFilterError):
    code = "library_filter_required"
    default_detail = "A rule must reference a library filter"


class LibraryFilterImmutable(LibraryFilterError):
    code = "library_filter_immutable"
    default_detail = "A rule cannot be moved to a different library filter"


class UniqueName(LibraryFilterError):
    code = "unique_name"
    default_detail = "A library filter with this name already exists"


class RuleRequired(LibraryFilterError):
    code = "rule_required"
    default_detail = "A library filter needs at least one rule before it can be active"


class DuplicateRule(LibraryFilterError):
    code = "duplicate_rule"
    default_detail = "This library filter already has a rule for that tag"


class TagRequired(LibraryFilterError):
    code = "tag_required"
    default_detail = "A tag rule must reference a tag"


class TagNotFound(LibraryFilterError):
    code = "tag_not_found"
    default_detail = "Tag not found"


class UnknownRuleType(LibraryFilterError):
    code = "unknown_rule_type"
    default_detail = "Unknown library filter rule type"


class TypeMismatch(LibraryFilterError):
    code = "type_mismatch"
    default_detail = "A rule's type cannot be changed"
