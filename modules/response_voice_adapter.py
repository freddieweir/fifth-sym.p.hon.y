"""
Response Voice Adapter

Converts LLM responses with code blocks, tables, and technical formatting
into natural voice-friendly output for ElevenLabs synthesis.

Maintains dual-output system:
- Visual: Full markdown with syntax highlighting
- Voice: Natural language summary without code syntax
"""

import re
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ParsedResponse:
    """
    Dual-output response structure.

    Attributes:
        visual: Full markdown response with code blocks
        voice: Natural language version for speech synthesis
        has_code: Whether response contains code blocks
        code_summary: Brief description of code changes
        has_tables: Whether response contains markdown tables
        has_links: Whether response contains hyperlinks
        complexity_score: 0-10 score of how technical the response is
    """
    visual: str
    voice: str
    has_code: bool = False
    code_summary: Optional[str] = None
    has_tables: bool = False
    has_links: bool = False
    complexity_score: int = 0


class ResponseVoiceAdapter:
    """
    Converts LLM responses to voice-friendly output.

    Features:
    - Strip code blocks (replace with natural language description)
    - Convert markdown tables to spoken summaries
    - Simplify technical explanations
    - Remove formatting that doesn't translate to voice
    - Preserve semantic meaning
    """

    # Code block language descriptors
    CODE_LANGUAGE_NAMES = {
        "python": "Python code",
        "py": "Python code",
        "javascript": "JavaScript code",
        "js": "JavaScript code",
        "typescript": "TypeScript code",
        "ts": "TypeScript code",
        "bash": "shell command",
        "sh": "shell script",
        "zsh": "shell command",
        "yaml": "YAML configuration",
        "yml": "YAML configuration",
        "json": "JSON data",
        "sql": "SQL query",
        "dockerfile": "Docker configuration",
        "html": "HTML markup",
        "css": "CSS styles",
        "markdown": "markdown text",
        "md": "markdown text",
        "rust": "Rust code",
        "go": "Go code",
        "java": "Java code",
        "c": "C code",
        "cpp": "C++ code",
        "csharp": "C# code",
        "ruby": "Ruby code",
        "php": "PHP code",
        "swift": "Swift code",
        "kotlin": "Kotlin code",
    }

    def __init__(self):
        """Initialize response voice adapter."""
        self.logger = logging.getLogger(__name__)

    def parse_response(self, markdown_text: str) -> ParsedResponse:
        """
        Parse LLM response into dual-output format.

        Args:
            markdown_text: Original markdown response from LLM

        Returns:
            ParsedResponse with visual and voice versions
        """
        # Start with original for visual
        visual = markdown_text

        # Analyze response structure
        has_code = self._has_code_blocks(markdown_text)
        has_tables = self._has_markdown_tables(markdown_text)
        has_links = self._has_markdown_links(markdown_text)

        # Extract code summary
        code_summary = None
        if has_code:
            code_summary = self._extract_code_summary(markdown_text)

        # Convert to voice-friendly format
        voice = self._convert_to_voice(markdown_text)

        # Calculate complexity score
        complexity_score = self._calculate_complexity(markdown_text)

        return ParsedResponse(
            visual=visual,
            voice=voice,
            has_code=has_code,
            code_summary=code_summary,
            has_tables=has_tables,
            has_links=has_links,
            complexity_score=complexity_score
        )

    def _has_code_blocks(self, text: str) -> bool:
        """Check if text contains code blocks."""
        return bool(re.search(r"```[\w]*\n", text))

    def _has_markdown_tables(self, text: str) -> bool:
        """Check if text contains markdown tables."""
        return bool(re.search(r"\|.*\|.*\|", text))

    def _has_markdown_links(self, text: str) -> bool:
        """Check if text contains markdown links."""
        return bool(re.search(r"\[([^\]]+)\]\(([^\)]+)\)", text))

    def _extract_code_summary(self, text: str) -> str:
        """
        Extract summary of code blocks in response.

        Args:
            text: Markdown text with code blocks

        Returns:
            Natural language summary of code
        """
        code_blocks = re.findall(r"```([\w]*)\n(.*?)```", text, re.DOTALL)

        if not code_blocks:
            return "code modifications"

        summaries = []
        for lang, code in code_blocks:
            lang_name = self.CODE_LANGUAGE_NAMES.get(lang.lower(), f"{lang} code" if lang else "code")

            # Try to infer what the code does
            lines = code.strip().split('\n')

            # For short code blocks, count lines
            if len(lines) <= 5:
                summaries.append(f"{len(lines)}-line {lang_name} snippet")
            else:
                summaries.append(f"{lang_name} block with {len(lines)} lines")

        if len(summaries) == 1:
            return summaries[0]
        else:
            return f"{len(summaries)} code blocks: " + ", ".join(summaries)

    def _convert_to_voice(self, text: str) -> str:
        """
        Convert markdown text to voice-friendly natural language.

        Args:
            text: Original markdown text

        Returns:
            Voice-friendly version
        """
        voice = text

        # 1. Replace code blocks with descriptions
        voice = self._replace_code_blocks(voice)

        # 2. Convert tables to natural language
        voice = self._convert_tables(voice)

        # 3. Strip markdown formatting
        voice = self._strip_markdown_formatting(voice)

        # 4. Simplify file paths (keep only filename)
        voice = self._simplify_file_paths(voice)

        # 5. Convert lists to natural language
        voice = self._convert_lists(voice)

        # 6. Remove excessive whitespace
        voice = self._clean_whitespace(voice)

        # 7. Limit length for voice (max ~500 chars for natural pacing)
        voice = self._limit_voice_length(voice)

        return voice.strip()

    def _replace_code_blocks(self, text: str) -> str:
        """Replace code blocks with natural language descriptions."""
        def replace_block(match):
            lang = match.group(1)
            code = match.group(2)

            lang_name = self.CODE_LANGUAGE_NAMES.get(lang.lower(), f"{lang} code" if lang else "code")

            # Try to extract function/class names
            function_match = re.search(r"(?:def|function|class|fn)\s+(\w+)", code)
            if function_match:
                name = function_match.group(1)
                return f"I've created a {name} {lang_name} function. "

            # Count lines for context
            lines = code.strip().split('\n')
            if len(lines) == 1:
                return f"Here's a {lang_name} one-liner. "
            else:
                return f"I've written {len(lines)} lines of {lang_name}. "

        return re.sub(r"```([\w]*)\n(.*?)```", replace_block, text, flags=re.DOTALL)

    def _convert_tables(self, text: str) -> str:
        """Convert markdown tables to natural language."""
        # Simple table detection
        table_pattern = r"\|[^\n]+\|[^\n]+\n\|[-:\s|]+\|[^\n]*\n(\|[^\n]+\n)+"

        def replace_table(match):
            table = match.group(0)
            rows = [r for r in table.split('\n') if r.strip() and not r.strip().startswith('|--')]

            if len(rows) <= 1:
                return "Here's a table with the information. "
            else:
                return f"I've created a table with {len(rows) - 1} rows of data. "

        return re.sub(table_pattern, replace_table, text)

    def _strip_markdown_formatting(self, text: str) -> str:
        """Remove markdown formatting that doesn't translate to voice."""
        # Remove headers (keep text)
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

        # Remove bold/italic (keep text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # **bold**
        text = re.sub(r"\*([^*]+)\*", r"\1", text)      # *italic*
        text = re.sub(r"__([^_]+)__", r"\1", text)      # __bold__
        text = re.sub(r"_([^_]+)_", r"\1", text)        # _italic_

        # Remove inline code (keep text)
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # Remove markdown links (keep link text)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

        # Remove horizontal rules
        text = re.sub(r"^[-*_]{3,}$", "", text, flags=re.MULTILINE)

        # Remove blockquotes
        text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

        return text

    def _simplify_file_paths(self, text: str) -> str:
        """Simplify file paths to just filenames for voice."""
        # Match absolute paths and replace with just filename
        text = re.sub(r"/[\w/.-]+/([\w.-]+)", r"\1", text)

        # Match relative paths with multiple directories
        text = re.sub(r"(?:[\w.-]+/){2,}([\w.-]+)", r"\1", text)

        return text

    def _convert_lists(self, text: str) -> str:
        """Convert markdown lists to natural language."""
        # Count list items
        list_items = re.findall(r"^[\s]*[-*+]\s+(.+)$", text, re.MULTILINE)

        if not list_items:
            return text

        # For short lists, read them
        if len(list_items) <= 3:
            # Remove list markers but keep items
            text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
            return text
        else:
            # For long lists, summarize
            list_pattern = r"(?:^[\s]*[-*+]\s+.+$\n?)+"
            replacement = f"I've listed {len(list_items)} items for you. "
            return re.sub(list_pattern, replacement, text, flags=re.MULTILINE)

    def _clean_whitespace(self, text: str) -> str:
        """Remove excessive whitespace."""
        # Replace multiple newlines with single space
        text = re.sub(r"\n\s*\n+", ". ", text)

        # Replace single newlines with spaces
        text = re.sub(r"\n", " ", text)

        # Remove multiple spaces
        text = re.sub(r"\s+", " ", text)

        return text

    def _limit_voice_length(self, text: str, max_length: int = 500) -> str:
        """
        Limit voice output length for natural pacing.

        Args:
            text: Voice text
            max_length: Maximum characters for voice output

        Returns:
            Truncated text if too long
        """
        if len(text) <= max_length:
            return text

        # Try to break at sentence boundary
        truncated = text[:max_length]
        last_period = truncated.rfind('. ')

        if last_period > max_length * 0.7:  # If we can break at sentence within 70% of max
            return truncated[:last_period + 1]
        else:
            return truncated[:max_length - 3] + "..."

    def _calculate_complexity(self, text: str) -> int:
        """
        Calculate complexity score (0-10) for response.

        Factors:
        - Code blocks
        - Tables
        - Technical terms
        - Length

        Args:
            text: Original markdown text

        Returns:
            Complexity score (0=simple, 10=very technical)
        """
        score = 0

        # Code blocks (+3 per block, max 6)
        code_blocks = len(re.findall(r"```", text)) // 2
        score += min(code_blocks * 3, 6)

        # Tables (+2 per table, max 4)
        tables = len(re.findall(r"\|.*\|.*\|", text))
        score += min(tables * 2, 4)

        # Technical terms (+1 per unique term, max 3)
        technical_terms = [
            "function", "class", "method", "variable", "array", "object",
            "async", "await", "promise", "callback", "API", "endpoint",
            "database", "query", "schema", "migration", "container", "docker"
        ]
        found_terms = sum(1 for term in technical_terms if term.lower() in text.lower())
        score += min(found_terms, 3)

        # Length (+1 if >1000 chars)
        if len(text) > 1000:
            score += 1

        return min(score, 10)

    def should_voice_response(self, parsed: ParsedResponse, threshold: int = 7) -> bool:
        """
        Determine if response should be voiced based on complexity.

        Args:
            parsed: ParsedResponse object
            threshold: Complexity threshold (0-10, default 7)

        Returns:
            True if response should be voiced, False if too complex
        """
        # Don't voice if too complex
        if parsed.complexity_score > threshold:
            self.logger.info(f"Response too complex for voice (score: {parsed.complexity_score})")
            return False

        # Don't voice if voice output is too short (just code description)
        if len(parsed.voice) < 20:
            self.logger.info("Voice output too short, skipping")
            return False

        return True


# Example usage
async def demo():
    """Demonstrate ResponseVoiceAdapter."""
    adapter = ResponseVoiceAdapter()

    # Example LLM response with code
    response = """
Here's the fix for your bug:

```python
def calculate_total(items: list[float]) -> float:
    return sum(items)
```

This function uses type hints for better code clarity. You can call it like:

```python
total = calculate_total([10.5, 20.3, 5.2])
```

The function will return the sum of all items.
"""

    parsed = adapter.parse_response(response)

    print("=== Visual Output ===")
    print(parsed.visual)
    print("\n=== Voice Output ===")
    print(parsed.voice)
    print(f"\n=== Metadata ===")
    print(f"Has code: {parsed.has_code}")
    print(f"Code summary: {parsed.code_summary}")
    print(f"Complexity: {parsed.complexity_score}/10")
    print(f"Should voice: {adapter.should_voice_response(parsed)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
