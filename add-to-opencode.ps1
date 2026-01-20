# PowerShell script to add Kalima MCP server to OpenCode
# This automates the interactive prompts

Write-Host "Adding Kalima MCP server to OpenCode..." -ForegroundColor Green

# Navigate to Kalima directory
Set-Location "C:\Codex\Kalima"

# Run opencode mcp add with automated inputs
# Inputs: name, command, args, (no env vars for now)
$inputs = @(
    "kalima",  # Server name
    "node",    # Command
    "C:/Codex/Kalima/packages/mcp-server/dist/index.js",  # Args (first)
    "",        # Args (second - empty to finish)
    "n"        # Add environment variables? No
)

$inputs | opencode mcp add

Write-Host "`nVerifying installation..." -ForegroundColor Yellow
opencode mcp list

Write-Host "`nKalima MCP server has been added!" -ForegroundColor Green
Write-Host "Start OpenCode from the Kalima directory to use it:" -ForegroundColor Cyan
Write-Host "  cd C:\Codex\Kalima" -ForegroundColor Gray
Write-Host "  opencode" -ForegroundColor Gray
