from django.core.management.base import BaseCommand, CommandError
from django.template.loader import get_template
from django.template.loader import TemplateDoesNotExist
from bs4 import BeautifulSoup
import json


class Command(BaseCommand):
    help = "Renders the specified template, splits it into head and body and writes it to the given output files"

    def add_arguments(self, parser):
        parser.add_argument("template")
        parser.add_argument("head_file")
        parser.add_argument("body_file")
        parser.add_argument("context", nargs="?")

    def handle(self, *args, **options):
        try:
            template = get_template(options["template"])
        except TemplateDoesNotExist:
            raise CommandError('Template "%s" does not exist' % options["template"])

        if options["context"]:
            context = json.loads(options["context"])
        else:
            context = {}
        html = template.render(context)

        soup = BeautifulSoup(html, "html.parser")
        with open(options["head_file"], "w") as f:
            f.write(soup.head.prettify())
        with open(options["body_file"], "w") as f:
            f.write(soup.body.prettify())
