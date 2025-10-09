#!/usr/bin/env python3
"""
Fifth Symphony - Avatar System Example

Demonstrates Visual Novel avatar with LED indicators.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from modules.avatar_emotion_engine import AvatarEmotionEngine
from modules.visualization_widget import AvatarState, VisualNovelWidget


def main():
    """Run avatar demo."""
    print("🎨 Fifth Symphony - Avatar System Demo")
    print("=" * 60)

    app = QApplication(sys.argv)

    # Create avatar
    avatar = VisualNovelWidget(always_on_top=True)
    avatar.resize(400, 500)
    avatar.show()

    print("\n✅ Avatar window created!")
    print("\n📊 Features:")
    print("  - Static image swapping (5 states)")
    print("  - LED indicators (5 colors)")
    print("  - Always-on-top desktop pet mode")
    print("  - Placeholder images (works without assets)")

    # Emotion engine
    emotion_engine = AvatarEmotionEngine()

    # Demo sequence
    demo_states = [
        ("Idle", AvatarState.IDLE, []),
        ("Voice Speaking", AvatarState.TALKING, [("voice", True, True)]),
        ("Microphone Recording", AvatarState.LISTENING, [("mic", True, True)]),
        ("AI Processing", AvatarState.PROCESSING, [("processing", True, True)]),
        ("Error State", AvatarState.ERROR, [("error", True, True)]),
        (
            "Multiple LEDs",
            AvatarState.IDLE,
            [("voice", True, False), ("mic", True, False), ("processing", True, False)],
        ),
    ]

    current_index = [0]

    def next_state():
        """Show next demo state."""
        if current_index[0] >= len(demo_states):
            # Reset
            current_index[0] = 0

        name, state, leds = demo_states[current_index[0]]

        print(f"\n🎭 Demo State {current_index[0] + 1}/{len(demo_states)}: {name}")

        # Reset LEDs
        for led_name in ["voice", "mic", "processing", "error", "special"]:
            avatar.set_led(led_name, False)

        # Set state
        avatar.set_state(state)

        # Set LEDs
        for led_name, active, pulsing in leds:
            avatar.set_led(led_name, active, pulsing)
            if active:
                print(f"  🔵 LED {led_name}: {'Pulsing' if pulsing else 'On'}")

        current_index[0] += 1

        # Schedule next
        QTimer.singleShot(3000, next_state)

    # Emotion demo
    def demo_emotions():
        """Demonstrate emotion detection."""
        print("\n" + "=" * 60)
        print("🤖 EMOTION DETECTION DEMO")
        print("=" * 60)

        test_messages = [
            "Success! Deployment complete!",
            "Error: Connection failed.",
            "Wow! Found something amazing!",
            "Analyzing repository structure...",
        ]

        for msg in test_messages:
            result = emotion_engine.detect_emotion(msg)
            print(f"\n📝 '{msg}'")
            print(f"  🎭 Emotion: {result.emotion.value}")
            print(f"  📊 Confidence: {result.confidence:.2f}")

    # Start demo
    print("\n🎬 Starting demo sequence...")
    print("  (States will change every 3 seconds)")

    QTimer.singleShot(1000, next_state)
    QTimer.singleShot(20000, demo_emotions)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
