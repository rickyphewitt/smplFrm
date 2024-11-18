from tempfile import template

import settings
import os
from random import Random
class TemplateService(object):

    def __init__(self):
        self.template_cache = self.__load_templates()


    def render(self, template_name, *args, **kwargs):
        if template_name in self.template_cache:
            template_raw = ""
            with open(self.template_cache[template_name], 'r') as t:
                template_raw = t.read()

            template_raw = self.__render(template_raw)

            for template_key, template_value in kwargs.items():
                template_raw = template_raw.replace(self.__wrap_template_var(template_key), str(template_value))

            return template_raw

        else:
            raise Exception(f"No template found with name {template_name}")

    def get_templates(self):
        return self.template_cache

    def __load_templates(self):
        templates = {}
        for template_dir in settings.TEMPLATE_DIRECTORIES:
            for dirpath, subdirs, filenames in os.walk(template_dir):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    templates[filename] = file_path


        return templates

    def __wrap_template_var(self, key):
        return "{{" + str(key) + "}}"

    def __render(self, template, **kwargs):
        """
        Render the template
        :param template:
        :return:
        """

        replacements = settings.TEMPLATE_VARS.copy()
        replacements.update(kwargs)

        for template_key, template_value in replacements.items():
            template = template.replace(self.__wrap_template_var(template_key), str(template_value))



        return template