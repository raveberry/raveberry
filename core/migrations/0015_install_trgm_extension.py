from django.db import migrations, connection

if connection.vendor == "postgresql":
    from django.contrib.postgres.operations import TrigramExtension


class Migration(migrations.Migration):
    dependencies = [("core", "0014_auto_20211011_2041")]

    operations = [TrigramExtension()] if connection.vendor == "postgresql" else []
