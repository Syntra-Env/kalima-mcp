"""Scholar MCP Server: Holonomic Research Environment.

Standardized on UOR Content Addressing and HUFD Field Dynamics.
"""

import signal
import sys
from mcp.server.fastmcp import FastMCP
from .db import get_connection, close_database
from .tools import identity, navigation, research, structural_analysis, context, workflow, discourse, hermeneutics
# from .utils.hufd_math import compute_information_geometric_metric

# Create FastMCP server
mcp = FastMCP("scholar-holonomic-server")

# Initialize mathematical metric
# conn = get_connection()
# compute_information_geometric_metric(conn)

# Register the clean research toolset
identity.register(mcp)
navigation.register(mcp)
research.register(mcp)
structural_analysis.register(mcp)
context.register(mcp)
workflow.register(mcp)
discourse.register(mcp)
hermeneutics.register(mcp)

def _cleanup(signum=None, frame=None):
    close_database()
    sys.exit(0)

signal.signal(signal.SIGINT, _cleanup)
signal.signal(signal.SIGTERM, _cleanup)

def main():
    mcp.run()

if __name__ == "__main__":
    main()
