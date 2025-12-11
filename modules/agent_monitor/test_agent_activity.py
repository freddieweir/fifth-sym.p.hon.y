#!/usr/bin/env python3
"""Test script to display Agent Activity module output."""

from agent_monitor.modules.agent_activity import AgentActivityMonitor

def main():
    print("🎭 Agent Activity Monitor Test\n")

    monitor = AgentActivityMonitor()

    print(f"Floor Guardians: {len(monitor.GUARDIANS)} agents")
    print(f"Pleiades Skills: {len(monitor.SKILLS)} skills")
    print(f"Active agents: {len(monitor.tracker.active_agents)}")
    print(f"Active skills: {len(monitor.tracker.active_skills)}")
    print(f"Agent history: {len(monitor.tracker.agent_last_used)} tracked")
    print(f"Skill history: {len(monitor.tracker.skill_last_used)} tracked\n")

    # Show a few sample entries
    print("Sample Floor Guardians:")
    for agent in list(monitor.GUARDIANS)[:5]:
        if agent in monitor.tracker.active_agents:
            status = "● Active"
        elif agent in monitor.tracker.agent_last_used:
            status = f"○ Last used recently"
        else:
            status = "○ Never used"
        print(f"  {agent:30} {status}")

    print("\nSample Pleiades Skills:")
    for skill in list(monitor.SKILLS)[:5]:
        if skill in monitor.tracker.active_skills:
            status = "● Active"
        elif skill in monitor.tracker.skill_last_used:
            status = f"● Last used recently"
        else:
            status = "○ Never used"
        print(f"  {skill:30} {status}")

    print("\n💡 To run the full TUI:")
    print("   uv run python -m agent_monitor.modules.agent_activity")

if __name__ == "__main__":
    main()
