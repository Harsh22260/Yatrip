from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created)
def install_vector_extension(sender, connection, **kwargs):
    """
    Make sure `vector` exists before any migration runs.

    The `chatbot` initial migration declares a `VectorField`, so the type has to
    be present while the table is being created. It is installed in the
    development database already, but Django's test runner builds a fresh
    database from a template and does not copy extensions into it, which made
    every `manage.py test` fail on `type "vector" does not exist` before a single
    test could run.

    `IF NOT EXISTS` keeps this a no-op on databases that already have it, and it
    is a no-op on backends other than PostgreSQL, which simply never fire this
    signal with a cursor that accepts the statement.
    """
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        cursor.execute('CREATE EXTENSION IF NOT EXISTS vector')


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot'