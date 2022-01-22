"""This module contains the rendertemplate command."""
import json

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import TemplateDoesNotExist, get_template


class Command(BaseCommand):
    """rendertemplate renders the given template with the given context. Used in testing."""

    help = "Renders the specified template writes the head and body tag to the given output files"

    def add_arguments(self, parser):
        parser.add_argument("template")
        parser.add_argument("head_file")
        parser.add_argument("body_file")
        parser.add_argument("context", nargs="?")

    def handle(self, *args, **options):
        try:
            template = get_template(options["template"])
        except TemplateDoesNotExist as error:
            raise CommandError(
                f"Template \"{options['template']}\" does not exist"
            ) from error

        if options["context"]:
            context = json.loads(options["context"])
        else:
            context = {}
        html = template.render(context)

        soup = BeautifulSoup(html, "html.parser")
        with open(options["head_file"], "w", encoding="utf-8") as head_file:
            head_file.write(soup.head.prettify())
        with open(options["body_file"], "w", encoding="utf-8") as body_file:
            body_file.write(soup.body.prettify())
