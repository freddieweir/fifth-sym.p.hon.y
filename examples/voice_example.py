#!/usr/bin/env python3
"""
Fifth Symphony - Voice System Example

Demonstrates voice permission system with code-free output.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.onepassword_manager import OnePasswordManager
from modules.response_voice_adapter import ResponseVoiceAdapter
from modules.voice_handler import VoiceHandler
from modules.voice_permission_hook import VoicePermissionHook, VoicePermissionResponse


async def permission_callback(request):
    """Simple permission callback for demo."""
    print(f"\n{'='*60}")
    print("🎤 VOICE PERMISSION REQUEST")
    print(f"{'='*60}")
    print(f"📝 Voice Output: {request.parsed.voice[:100]}...")
    print(f"📊 Complexity: {request.parsed.complexity_score}/10")
    print(f"💻 Has Code: {request.parsed.has_code}")

    if request.parsed.has_code:
        print(f"🔧 Code Summary: {request.parsed.code_summary}")

    print(f"\n{'='*60}")
    print("Options: (y)es, (n)o, (a)lways, (v)never, (m)ute")
    print(f"{'='*60}")

    # Auto-approve for demo
    print("✅ Auto-approved for demo\n")
    return VoicePermissionResponse.YES


async def main():
    """Run voice system demo."""
    print("🎵 Fifth Symphony - Voice System Demo")
    print("="*60)

    # Initialize components
    print("\n📦 Initializing...")

    op_manager = OnePasswordManager({})
    voice_handler = VoiceHandler({"enabled": True}, op_manager)
    voice_hook = VoicePermissionHook(
        voice_handler=voice_handler,
        config={"complexity_threshold": 7},
        permission_callback=permission_callback
    )

    print("✅ Voice system ready!\n")

    # Test cases
    test_cases = [
        {
            "name": "Simple Text",
            "response": "Hello! This is a simple response."
        },
        {
            "name": "Code Response",
            "response": """
Here's the fix for your bug:

```python
def calculate_total(items):
    return sum(items)
```

This function adds up all items in a list.
"""
        },
        {
            "name": "Complex Technical",
            "response": """
The system uses asynchronous I/O with event-driven architecture.

```python
async def process_request(data):
    result = await api.fetch(data)
    return result
```

Configure the timeout in settings.yaml:
```yaml
timeout: 30
retries: 3
```
"""
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}/{len(test_cases)}: {test['name']}")
        print(f"{'='*60}\n")

        print("📥 Original Response:")
        print(test["response"])
        print()

        # Process through voice adapter
        adapter = ResponseVoiceAdapter()
        parsed = adapter.parse_response(test["response"])

        print("🎤 Voice-Friendly Version:")
        print(parsed.voice)
        print()

        print("📊 Analysis:")
        print(f"  - Complexity: {parsed.complexity_score}/10")
        print(f"  - Has code: {parsed.has_code}")
        print(f"  - Code summary: {parsed.code_summary or 'N/A'}")
        print(f"  - Should voice: {adapter.should_voice_response(parsed)}")

        # Process through permission hook
        await voice_hook.on_response(test["response"])

        await asyncio.sleep(1)

    print(f"\n{'='*60}")
    print("✅ Voice system demo complete!")
    print(f"{'='*60}\n")

    print("💡 Key Features Demonstrated:")
    print("  - Code blocks removed from voice output")
    print("  - Technical jargon simplified")
    print("  - Complexity scoring")
    print("  - Permission request system")


if __name__ == "__main__":
    asyncio.run(main())
