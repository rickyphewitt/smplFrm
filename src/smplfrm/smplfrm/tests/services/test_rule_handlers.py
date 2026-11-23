from django.db.models import Q
from django.test import TestCase

from smplfrm.models import Image, ImageTag, LibraryFilter, LibraryFilterRule, Tag
from smplfrm.services.library_filter.rule_handlers import (
    JSONAPI_TYPE_TO_RULE_TYPE,
    RULE_TYPE_HANDLERS,
    RULE_TYPE_TO_JSONAPI_TYPE,
)
from smplfrm.services.library_filter.rule_handlers.tag import TagRuleHandler


class TestRuleTypeRegistry(TestCase):
    def test_every_model_rule_type_has_a_handler(self):
        self.assertEqual(
            set(RULE_TYPE_HANDLERS), set(LibraryFilterRule.RuleType.values)
        )

    def test_tag_handler_is_registered(self):
        self.assertIsInstance(RULE_TYPE_HANDLERS["tag"], TagRuleHandler)

    def test_jsonapi_type_maps_are_inverse(self):
        self.assertEqual(RULE_TYPE_TO_JSONAPI_TYPE, {"tag": "tag_library_filter_rules"})
        self.assertEqual(JSONAPI_TYPE_TO_RULE_TYPE, {"tag_library_filter_rules": "tag"})


class TestTagRuleHandler(TestCase):
    def setUp(self):
        self.library_filter = LibraryFilter.objects.create(name="frame")
        self.frame = Tag.objects.create(value="frame", display_value="Frame")
        self.frames = Tag.objects.create(value="frames", display_value="Frames")
        self.rule = LibraryFilterRule.objects.create(
            library_filter=self.library_filter, tag=self.frame
        )

    def make_image(self, name, *tags):
        image = Image.objects.create(
            name=name, file_name=name, file_path=f"/library/{name}"
        )
        for tag in tags:
            ImageTag.objects.create(image=image, tag=tag)
        return image

    def test_to_q_matches_the_rule_tag_value(self):
        self.assertEqual(
            TagRuleHandler().to_q(self.rule), Q(image_tags__tag__value="frame")
        )

    def test_to_q_selects_only_images_with_the_exact_tag(self):
        tagged = self.make_image("tagged.jpg", self.frame)
        self.make_image("similar.jpg", self.frames)
        self.make_image("plain.jpg")

        matched = Image.objects.filter(TagRuleHandler().to_q(self.rule))

        self.assertEqual(list(matched), [tagged])
