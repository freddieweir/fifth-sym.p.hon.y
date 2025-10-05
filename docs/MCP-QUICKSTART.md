# MCP (Model Context Protocol) Quick Start

Quick reference for using MCP servers with Fifth Symphony.

## 🎯 What is MCP?

**Model Context Protocol** = Standardized way for AI assistants (like Claude) to use tools and access data.

**Think of it as**: API for AI agents

## 📍 MCP Server Locations

### External MCP (Third-Party)
```
/Users/fweir/git/external/mcp/
└── elevenlabs-mcp/          # Official ElevenLabs voice synthesis
```

### Internal MCP (Personal)
```
/Users/fweir/git/internal/mcp/
└── (Your custom MCP servers)
```

### VM MCP (Sandbox)
```
/Volumes/aetherium/Shared Parallel/macOS Dev Files/virtualgit/mcp/
└── (Testing/experimental MCP servers)
```

## 🚀 Quick Usage

### Running an MCP Server

```bash
# Development mode with mcpo proxy
uvx mcpo --port 8000 -- uvx elevenlabs-mcp

# Access interactive API docs
open http://localhost:8000/docs
```

### ElevenLabs MCP Example

**Already Integrated!** Fifth Symphony uses ElevenLabs MCP via `modules/orchestrator/mcp_client.py`

```python
from modules.orchestrator.mcp_client import MCPClient

# Initialize client
mcp_client = MCPClient(config)

# Synthesize speech
await mcp_client.speak("Permission requested!")

# Generate audio file
audio_path = await mcp_client.synthesize_speech(
    "This is a test",
    output_path=Path("/tmp/test.mp3")
)
```

## 📚 Available MCP Servers

### ElevenLabs Voice Synthesis

**Location**: `/Users/fweir/git/external/mcp/elevenlabs-mcp`

**Features**:
- Text-to-speech
- Voice cloning
- Audio transcription
- Sound effect generation

**Fifth Symphony Integration**:
- Used in `modules/orchestrator/mcp_client.py`
- Voice feedback for permission requests
- Risk-appropriate tone and urgency

### Other MCP Servers (To Explore)

Check `/Users/fweir/git/external/mcp/` for additional installed servers.

## 🔧 Claude Desktop Integration

To use MCP servers with Claude Desktop:

**Edit**: `~/.config/claude/config.json`

```json
{
  "mcpServers": {
    "elevenlabs": {
      "command": "uvx",
      "args": ["elevenlabs-mcp"],
      "env": {
        "ELEVENLABS_API_KEY": "get_from_1password"
      }
    }
  }
}
```

## 🎵 Fifth Symphony MCP Integration

### Current Integration

**ElevenLabs MCP** → `mcp_client.py` → Voice feedback system

### Future MCP Opportunities

1. **AniList MCP**
   - Wrap `anilist_client.py` as MCP server
   - Expose GraphQL operations as MCP tools
   - Share across projects

2. **1Password MCP**
   - Secure credential retrieval
   - Prompt management via MCP
   - Cross-project secret access

3. **Fifth Symphony Orchestrator MCP**
   - Expose permission engine as MCP
   - Other projects can request approvals
   - Centralized permission system

## 📖 MCP Resources

### Official Docs
- MCP Specification: https://github.com/modelcontextprotocol
- ElevenLabs MCP: `/Users/fweir/git/external/mcp/elevenlabs-mcp/README.md`

### Local Examples
Check external repos for MCP implementations:
- `/Users/fweir/git/external/repos/agentic-tools/` - May have MCP examples
- `/Users/fweir/git/external/repos/assistant-tools/` - AI assistant MCP patterns

## 🛠️ Creating Your Own MCP Server

### Basic Structure

```python
# my_mcp_server.py
import asyncio
from mcp import Server, Tool

server = Server("my-server")

@server.tool()
async def my_tool(param: str) -> str:
    """Tool description"""
    return f"Processed: {param}"

if __name__ == "__main__":
    asyncio.run(server.run())
```

### Running with mcpo

```bash
# Expose as REST API
uvx mcpo --port 8000 -- python my_mcp_server.py

# Test
curl http://localhost:8000/tools/my_tool -d '{"param": "test"}'
```

## 🎯 Quick Commands

```bash
# Update external MCP servers
cd /Users/fweir/git/external/mcp/elevenlabs-mcp
git pull

# Test ElevenLabs MCP
uvx elevenlabs-mcp --help

# Run MCP with proxy
uvx mcpo --port 8000 -- uvx elevenlabs-mcp

# Check MCP server status
curl http://localhost:8000/health
```

## 💡 Tips

1. **Use mcpo for development** - Interactive API docs at `/docs`
2. **Check external repos** - May have MCP examples
3. **VM for testing** - Use VM Claude for risky MCP experiments
4. **Share across projects** - MCP servers work for all your repos

---

**Note**: This is a quick reference. For detailed MCP documentation, check official spec and external repo examples.
