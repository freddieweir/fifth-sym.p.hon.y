#!/usr/bin/env python3
"""
OPML to Text Converter

Parses OPML (Outline Processor Markup Language) files and outputs RSS feeds
in a clean, readable text format.

Usage:
    python opml_to_txt.py input.opml [output.txt]

If output file is not specified, outputs to stdout.
"""

import sys
import warnings
from pathlib import Path

try:
    from defusedxml import ElementTree
    from defusedxml.ElementTree import parse as safe_parse
except ImportError:
    # Fallback to standard library with warning
    # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
    from xml import etree  # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
    # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
    from xml.etree.ElementTree import parse as safe_parse  # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml

    ElementTree = etree.ElementTree
    warnings.warn(
        "defusedxml not installed. Using standard xml library. "
        "Install defusedxml for better security: pip install defusedxml",
        UserWarning,
        stacklevel=2
    )


class OPMLParser:
    """Parses OPML files and extracts RSS feed information."""

    def __init__(self, opml_path: str):
        """Initialize parser with OPML file path."""
        self.opml_path = Path(opml_path)
        self.feeds = []
        self.categories = {}
        self.title = ""

    def parse(self) -> tuple[str, dict[str, list[dict]]]:
        """Parse the OPML file and return title and categorized feeds."""
        try:
            tree = safe_parse(self.opml_path)
            root = tree.getroot()

            # Extract title from head
            head = root.find("head")
            if head is not None:
                title_elem = head.find("title")
                if title_elem is not None:
                    self.title = title_elem.text or "OPML Feeds"

            # Parse body for feeds
            body = root.find("body")
            if body is not None:
                self._parse_outlines(body, category="Uncategorized")

            return self.title, self.categories

        except ElementTree.ParseError as e:
            raise ValueError(f"Invalid OPML file: {e}") from e
        except FileNotFoundError as e:
            raise FileNotFoundError(f"OPML file not found: {self.opml_path}") from e

    def _parse_outlines(self, element: ElementTree.Element, category: str = "Uncategorized"):
        """Recursively parse outline elements."""
        for outline in element.findall("outline"):
            # Check if this is a category/folder
            if outline.get("type") != "rss" and outline.get("xmlUrl") is None:
                # This is a category/folder
                category_name = outline.get("text") or outline.get("title") or category
                # Parse children with this category
                self._parse_outlines(outline, category_name)
            else:
                # This is a feed
                feed_info = self._extract_feed_info(outline)
                if feed_info:
                    if category not in self.categories:
                        self.categories[category] = []
                    self.categories[category].append(feed_info)

    def _extract_feed_info(self, outline: ElementTree.Element) -> dict | None:
        """Extract feed information from an outline element."""
        xml_url = outline.get("xmlUrl")
        if not xml_url:
            return None

        return {
            "title": outline.get("text") or outline.get("title") or "Untitled Feed",
            "xml_url": xml_url,
            "html_url": outline.get("htmlUrl", ""),
            "description": outline.get("description", ""),
            "type": outline.get("type", "rss")
        }


class TextFormatter:
    """Formats parsed OPML data into readable text."""

    @staticmethod
    def format_feeds(title: str, categories: dict[str, list[dict]],
                     show_urls: bool = True, show_descriptions: bool = True) -> str:
        """Format feeds into readable text output."""
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append(f"📚 {title}")
        lines.append("=" * 80)
        lines.append("")

        # Statistics
        total_feeds = sum(len(feeds) for feeds in categories.values())
        lines.append(f"📊 Total Feeds: {total_feeds}")
        lines.append(f"📁 Categories: {len(categories)}")
        lines.append("")
        lines.append("-" * 80)
        lines.append("")

        # Categories and feeds
        for idx, (category, feeds) in enumerate(categories.items(), 1):
            # Category header
            lines.append(f"📁 [{idx}] {category} ({len(feeds)} feeds)")
            lines.append("─" * 40)

            # Feeds in category
            for feed_idx, feed in enumerate(feeds, 1):
                lines.append(f"  {feed_idx}. 📰 {feed['title']}")

                if show_urls:
                    if feed["html_url"]:
                        lines.append(f"     🌐 Website: {feed['html_url']}")
                    lines.append(f"     📡 RSS: {feed['xml_url']}")

                if show_descriptions and feed["description"]:
                    lines.append(f"     📝 {feed['description']}")

                lines.append("")

            lines.append("")

        # Footer
        lines.append("-" * 80)
        lines.append(f"Generated from: {Path(sys.argv[1]).name}")

        return "\n".join(lines)

    @staticmethod
    def format_simple(categories: dict[str, list[dict]]) -> str:
        """Format feeds in a simple, compact format."""
        lines = []

        for category, feeds in categories.items():
            lines.append(f"\n[{category}]")
            for feed in feeds:
                lines.append(f"  • {feed['title']}: {feed['xml_url']}")

        return "\n".join(lines)


def main():
    """Main entry point for the script."""
    # Parse command line arguments
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    opml_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        # Parse OPML
        parser = OPMLParser(opml_file)
        title, categories = parser.parse()

        if not categories:
            print("No feeds found in the OPML file.")
            sys.exit(1)

        # Format output
        formatter = TextFormatter()
        output = formatter.format_feeds(title, categories)

        # Write output
        if output_file:
            output_path = Path(output_file)
            output_path.write_text(output, encoding="utf-8")
            print(f"✅ Successfully wrote {sum(len(feeds) for feeds in categories.values())} feeds to {output_file}")
        else:
            print(output)

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
