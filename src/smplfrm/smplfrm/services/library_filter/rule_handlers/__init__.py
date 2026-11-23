"""Registry of library filter rule types.

Each handler turns one rule row into a Django ``Q`` predicate over ``Image``.
Code that needs to apply rules iterates this registry instead of importing a
handler by name, the same way plugins and themes are looked up in
``PLUGIN_REGISTRY`` and ``THEME_REGISTRY``.

Adding a rule type: add a ``LibraryFilterRule.RuleType`` choice and its
column, a handler here, and a serializer for its JSON:API type.
"""

from typing import Dict, Protocol

from django.db.models import Q

from smplfrm.models import LibraryFilterRule

from .tag import TagRuleHandler


class RuleHandler(Protocol):
    rule_type: str
    jsonapi_type: str

    def to_q(self, rule: LibraryFilterRule) -> Q: ...


RULE_TYPE_HANDLERS: Dict[str, RuleHandler] = {
    TagRuleHandler.rule_type: TagRuleHandler(),
}

RULE_TYPE_TO_JSONAPI_TYPE: Dict[str, str] = {
    rule_type: handler.jsonapi_type for rule_type, handler in RULE_TYPE_HANDLERS.items()
}

JSONAPI_TYPE_TO_RULE_TYPE: Dict[str, str] = {
    jsonapi_type: rule_type
    for rule_type, jsonapi_type in RULE_TYPE_TO_JSONAPI_TYPE.items()
}
