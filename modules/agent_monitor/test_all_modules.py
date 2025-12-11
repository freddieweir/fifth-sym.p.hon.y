#!/usr/bin/env python3
"""Test all modular TUI components."""

def test_module(module_name, class_name):
    """Test importing and initializing a module."""
    try:
        if module_name == "agent_activity":
            from agent_monitor.modules.agent_activity import AgentActivityMonitor
            monitor = AgentActivityMonitor()
            stats = f"{len(monitor.GUARDIANS)} guardians, {len(monitor.SKILLS)} skills"
        elif module_name == "infrastructure":
            from agent_monitor.modules.infrastructure import InfrastructureMonitor
            monitor = InfrastructureMonitor()
            stats = f"{len(monitor.mcp_manager.servers)} MCP servers, {len(monitor.OBSERVATORY_SERVICES)} services"
        elif module_name == "content":
            from agent_monitor.modules.content import ContentMonitor
            monitor = ContentMonitor()
            stats = f"{len(monitor.audio_files)} audio, {len(monitor.doc_files)} docs"
        elif module_name == "system_status":
            from agent_monitor.modules.system_status import SystemStatusMonitor
            monitor = SystemStatusMonitor()
            stats = f"{len(monitor.context_files)} context files"
        else:
            return False, "Unknown module"

        return True, stats

    except Exception as e:
        return False, str(e)


def main():
    """Test all modules."""
    print("🧪 Testing Albedo Agent Monitor Modules\n")

    modules = [
        ("agent_activity", "AgentActivityMonitor"),
        ("infrastructure", "InfrastructureMonitor"),
        ("content", "ContentMonitor"),
        ("system_status", "SystemStatusMonitor")
    ]

    results = []
    for module_name, class_name in modules:
        print(f"Testing {module_name}...", end=" ")
        success, info = test_module(module_name, class_name)

        if success:
            print(f"✅ OK - {info}")
            results.append(True)
        else:
            print(f"❌ FAILED - {info}")
            results.append(False)

    print()

    # Test shared utilities
    print("Testing shared utilities...", end=" ")
    try:
        from agent_monitor.shared import (
            Colors, Symbols, ModuleConfig, KeyboardHandler,
            RichTableBuilder, AgentTracker, MCPManager
        )
        print(f"✅ OK - All 7 utilities import correctly")
        results.append(True)
    except Exception as e:
        print(f"❌ FAILED - {e}")
        results.append(False)

    print()

    # Summary
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print()
        print("✨ Ready to launch:")
        print("   python launch_modules.py")
        print()
        print("Or run individual modules:")
        print("   uv run python -m agent_monitor.modules.agent_activity")
        print("   uv run python -m agent_monitor.modules.infrastructure")
        print("   uv run python -m agent_monitor.modules.content")
        print("   uv run python -m agent_monitor.modules.system_status")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
