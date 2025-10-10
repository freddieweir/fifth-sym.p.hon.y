"""
Avatar Emotion Engine

Intelligent emotion detection and mapping for avatar image selection.
Analyzes LLM responses, system events, and context to choose appropriate emotions.

Future integration with Visual Novel widget for dynamic emotional expressions.
"""

import logging
import re
from typing import Dict, Optional, List
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class Emotion(Enum):
    """
    Avatar emotions.

    Each emotion maps to a specific avatar image in the emotions/ directory.
    """

    NEUTRAL = "neutral"  # Default state
    HAPPY = "happy"  # Success, completion, positive feedback
    SAD = "sad"  # Errors, failures, problems
    SURPRISED = "surprised"  # Unexpected events, discoveries
    THINKING = "thinking"  # Deep processing, complex queries
    EXCITED = "excited"  # New downloads, achievements
    CONFUSED = "confused"  # Unclear input, need clarification
    WORRIED = "worried"  # Warnings, potential issues
    PROUD = "proud"  # Major accomplishments
    CALM = "calm"  # Meditation, waiting states


@dataclass
class EmotionScore:
    """
    Emotion detection score.

    Attributes:
        emotion: Detected emotion
        confidence: Confidence level (0.0-1.0)
        triggers: What triggered this emotion
    """

    emotion: Emotion
    confidence: float
    triggers: List[str]


class AvatarEmotionEngine:
    """
    Detects emotions from text and system events.

    Features:
    - Keyword-based emotion detection
    - Context-aware emotion selection
    - Confidence scoring
    - Emotion history tracking
    """

    # Emotion keyword patterns
    EMOTION_PATTERNS = {
        Emotion.HAPPY: [
            r"\b(success|complete|done|finished|ready|great|perfect|excellent)\b",
            r"✅|✓",
            r"\b(deployed|created|built|implemented)\b",
        ],
        Emotion.SAD: [
            r"\b(error|fail|failed|failure|problem|issue|broken)\b",
            r"❌|✗",
            r"\b(cannot|unable|couldn't|can't)\b",
        ],
        Emotion.SURPRISED: [
            r"!{2,}",
            r"\b(wow|whoa|amazing|unexpected|discovered|found)\b",
            r"\b(new|novel|unique|rare)\b",
        ],
        Emotion.THINKING: [
            r"\b(analyzing|processing|calculating|computing|thinking)\b",
            r"🤔",
            r"\b(consider|evaluate|assess|review)\b",
        ],
        Emotion.EXCITED: [
            r"!",
            r"\b(new download|achievement|milestone|breakthrough)\b",
            r"\b(awesome|fantastic|incredible)\b",
        ],
        Emotion.CONFUSED: [
            r"\?{2,}",
            r"\b(unclear|confusing|confused|unsure|uncertain)\b",
            r"\b(what|which|clarify|explain)\b",
        ],
        Emotion.WORRIED: [
            r"\b(warning|caution|careful|attention|alert)\b",
            r"⚠️",
            r"\b(might|may|could|potential)\b",
        ],
        Emotion.PROUD: [
            r"\b(accomplished|achieved|succeeded|completed successfully)\b",
            r"🎉|🎊",
            r"\b(milestone|victory|triumph)\b",
        ],
        Emotion.CALM: [
            r"\b(waiting|idle|rest|calm|peaceful|quiet)\b",
            r"\b(standby|ready|available)\b",
        ],
    }

    # Emotion priorities (higher = more important)
    EMOTION_PRIORITY = {
        Emotion.SAD: 10,  # Errors are critical
        Emotion.WORRIED: 9,  # Warnings are important
        Emotion.EXCITED: 8,  # Excitement overrides most
        Emotion.SURPRISED: 7,  # Surprise is notable
        Emotion.HAPPY: 6,  # Happiness is positive
        Emotion.PROUD: 6,  # Pride is positive
        Emotion.THINKING: 5,  # Thinking is moderate
        Emotion.CONFUSED: 5,  # Confusion is moderate
        Emotion.CALM: 3,  # Calm is low priority
        Emotion.NEUTRAL: 1,  # Neutral is default
    }

    def __init__(self):
        """Initialize emotion engine."""
        self.current_emotion = Emotion.NEUTRAL
        self.emotion_history: List[EmotionScore] = []
        self.max_history = 10

    def detect_emotion(self, text: str, context: Optional[Dict] = None) -> EmotionScore:
        """
        Detect emotion from text and context.

        Args:
            text: Text to analyze
            context: Optional context dictionary

        Returns:
            EmotionScore with detected emotion and confidence
        """
        scores: Dict[Emotion, float] = {}
        triggers: Dict[Emotion, List[str]] = {}

        # Analyze text for emotion keywords
        text_lower = text.lower()

        for emotion, patterns in self.EMOTION_PATTERNS.items():
            emotion_score = 0.0
            emotion_triggers = []

            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                if matches:
                    # Each match increases confidence
                    emotion_score += 0.3 * len(matches)
                    emotion_triggers.append(pattern)

            if emotion_score > 0:
                scores[emotion] = min(emotion_score, 1.0)  # Cap at 1.0
                triggers[emotion] = emotion_triggers

        # Context-based adjustments
        if context:
            self._apply_context(scores, triggers, context)

        # If no emotions detected, default to NEUTRAL
        if not scores:
            return EmotionScore(emotion=Emotion.NEUTRAL, confidence=1.0, triggers=["default"])

        # Select emotion with highest score (weighted by priority)
        best_emotion = max(
            scores.items(), key=lambda x: x[1] * (self.EMOTION_PRIORITY.get(x[0], 1) / 10)
        )

        emotion, confidence = best_emotion

        result = EmotionScore(
            emotion=emotion, confidence=confidence, triggers=triggers.get(emotion, [])
        )

        # Update history
        self.emotion_history.append(result)
        if len(self.emotion_history) > self.max_history:
            self.emotion_history.pop(0)

        self.current_emotion = emotion

        logger.info(f"Detected emotion: {emotion.value} (confidence: {confidence:.2f})")

        return result

    def _apply_context(
        self, scores: Dict[Emotion, float], triggers: Dict[Emotion, List[str]], context: Dict
    ):
        """
        Apply context-based adjustments to emotion scores.

        Args:
            scores: Emotion scores dictionary
            triggers: Emotion triggers dictionary
            context: Context dictionary
        """
        # Voice output context
        if context.get("voice_speaking"):
            scores[Emotion.HAPPY] = scores.get(Emotion.HAPPY, 0) + 0.2

        # Processing context
        if context.get("processing"):
            scores[Emotion.THINKING] = scores.get(Emotion.THINKING, 0) + 0.3

        # Error context
        if context.get("error"):
            scores[Emotion.SAD] = scores.get(Emotion.SAD, 0) + 0.5

        # New file context
        if context.get("new_file"):
            scores[Emotion.EXCITED] = scores.get(Emotion.EXCITED, 0) + 0.3

        # Completion context
        if context.get("completed"):
            scores[Emotion.PROUD] = scores.get(Emotion.PROUD, 0) + 0.4

    def get_emotion_for_state(self, state: str) -> Emotion:
        """
        Get appropriate emotion for avatar state.

        Args:
            state: Avatar state (idle, talking, listening, processing, error)

        Returns:
            Recommended emotion
        """
        state_emotions = {
            "idle": Emotion.NEUTRAL,
            "talking": Emotion.HAPPY,  # Usually speaking good news
            "listening": Emotion.CALM,  # Attentive listening
            "processing": Emotion.THINKING,
            "error": Emotion.SAD,
        }

        return state_emotions.get(state.lower(), Emotion.NEUTRAL)

    def get_recent_emotions(self, count: int = 5) -> List[EmotionScore]:
        """
        Get recent emotion history.

        Args:
            count: Number of recent emotions to return

        Returns:
            List of recent EmotionScores
        """
        return self.emotion_history[-count:]

    def get_dominant_emotion(self, window: int = 5) -> Emotion:
        """
        Get dominant emotion from recent history.

        Args:
            window: Number of recent emotions to consider

        Returns:
            Most common emotion in window
        """
        recent = self.get_recent_emotions(window)

        if not recent:
            return Emotion.NEUTRAL

        # Count emotions
        emotion_counts: Dict[Emotion, int] = {}
        for score in recent:
            emotion_counts[score.emotion] = emotion_counts.get(score.emotion, 0) + 1

        # Return most common
        dominant = max(emotion_counts.items(), key=lambda x: x[1])
        return dominant[0]


# Example usage
def demo():
    """Demonstrate emotion detection."""
    engine = AvatarEmotionEngine()

    test_texts = [
        "Success! The deployment is complete and everything is working perfectly.",
        "Error: Failed to connect to database. Connection refused.",
        "Wow! I found a new feature in the codebase!",
        "Analyzing the repository structure... This might take a moment.",
        "Warning: This operation might cause data loss. Proceed with caution?",
        "I'm not sure what you mean. Could you clarify your request?",
        "🎉 Congratulations! You've reached 1000 commits!",
    ]

    for text in test_texts:
        result = engine.detect_emotion(text)
        print(f"\nText: {text}")
        print(f"Emotion: {result.emotion.value}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Triggers: {result.triggers}")


if __name__ == "__main__":
    demo()
