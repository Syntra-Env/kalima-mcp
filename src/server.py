"""Kalima MCP Server entry point."""

import signal
import sys

from mcp.server.fastmcp import FastMCP

from .db import close_database
from .tools import quran, context, research, linguistic, workflow

# Create FastMCP server
mcp = FastMCP("kalima-mcp-server")

# Register all tool modules
quran.register(mcp)
context.register(mcp)
research.register(mcp)
linguistic.register(mcp)
workflow.register(mcp)


def _cleanup(signum=None, frame=None):
    close_database()
    sys.exit(0)


signal.signal(signal.SIGINT, _cleanup)
signal.signal(signal.SIGTERM, _cleanup)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
