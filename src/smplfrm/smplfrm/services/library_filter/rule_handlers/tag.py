from django.db.models import Q

from smplfrm.models import LibraryFilterRule


class TagRuleHandler:
    """Matches images that carry the rule's tag (exact canonical value)."""

    rule_type = LibraryFilterRule.RuleType.TAG.value
    jsonapi_type = "tag_library_filter_rules"

    def to_q(self, rule: LibraryFilterRule) -> Q:
        """Return a predicate over Image for this rule."""
        return Q(image_tags__tag__value=rule.tag.value)
