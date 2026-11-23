"""Serializers for library filter rules, one per rule type."""

from smplfrm.models import LibraryFilterRule

from .tag import TagLibraryFilterRuleSerializer

RULE_SERIALIZERS = {
    LibraryFilterRule.RuleType.TAG.value: TagLibraryFilterRuleSerializer,
}

__all__ = ["RULE_SERIALIZERS", "TagLibraryFilterRuleSerializer"]
