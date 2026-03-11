"""Kalima MCP Server: Holonomic Research Environment.

Standardized on UOR Content Addressing and HUFD Field Dynamics.
"""

import signal
import sys
from mcp.server.fastmcp import FastMCP
from .db import close_database
from .tools import manifold, navigation, research, analytics, context, workflow

# Create FastMCP server
mcp = FastMCP("kalima-holonomic-server")

# Register the clean research toolset
manifold.register(mcp)
navigation.register(mcp)
research.register(mcp)
analytics.register(mcp)
context.register(mcp)
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
