from django.db import models

from smplfrm.models.base import ModelBase


class LibraryFilterRule(ModelBase):
    """One condition of a LibraryFilter.

    rule_type selects which typed column holds the condition. A new rule type
    adds its own nullable column; the "tag" type uses ``tag``.
    """

    class RuleType(models.TextChoices):
        TAG = "tag", "Tag"

    library_filter = models.ForeignKey(
        "smplfrm.LibraryFilter", on_delete=models.CASCADE, related_name="rules"
    )
    rule_type = models.CharField(
        max_length=20, choices=RuleType.choices, default=RuleType.TAG
    )
    tag = models.ForeignKey(
        "smplfrm.Tag",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="library_filter_rules",
    )

    class Meta:
        db_table = "library_filter_rule"
        constraints = [
            models.UniqueConstraint(
                fields=["library_filter", "tag"],
                condition=models.Q(rule_type="tag") & models.Q(deleted=False),
                name="uniq_tag_rule_per_filter",
            ),
        ]
        indexes = [models.Index(fields=["library_filter", "rule_type"])]
