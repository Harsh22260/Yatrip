"""Run the Yatrip MCP server from manage.py."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Serve the Yatrip MCP server (Yatrip catalogue + open data tools)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--transport",
            default=settings.MCP_SERVER_TRANSPORT,
            choices=["stdio", "sse", "streamable-http"],
            help="Transport to serve on (default: MCP_SERVER_TRANSPORT, 'stdio').",
        )
        parser.add_argument(
            "--host", default="127.0.0.1", help="Bind host for HTTP transports."
        )
        parser.add_argument(
            "--port", type=int, default=8000, help="Bind port for HTTP transports."
        )

    def handle(self, *args, **options):
        from yatrip.mcp_server import mcp

        transport = options["transport"]
        host = options["host"]
        port = options["port"]

        if transport != "stdio":
            mcp.settings.host = host
            mcp.settings.port = port

        self.stdout.write(
            self.style.SUCCESS(
                f"Yatrip MCP server starting on {transport} "
                f"(db={settings.DATABASES['default']['NAME']})"
            )
        )

        try:
            mcp.run(transport=transport)
        except KeyboardInterrupt:
            self.stdout.write("MCP server stopped.")
        except ImportError as exc:
            raise CommandError(
                f"Missing MCP dependencies: {exc}. Install with: pip install mcp"
            ) from exc
