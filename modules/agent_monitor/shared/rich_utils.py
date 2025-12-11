"""Rich library helpers for consistent styling across modules."""

from rich.table import Table
from rich.panel import Panel
from rich import box
from typing import List, Tuple, Any, Dict


class RichTableBuilder:
    """Build consistently styled Rich tables and panels."""

    @staticmethod
    def create_table(
        border_style: str = "cyan",
        columns: List[Tuple[str, Dict[str, Any]]] = None,
        **kwargs
    ) -> Table:
        """Create table with standard styling.

        Args:
            border_style: Color for table border
            columns: List of (name, column_kwargs) tuples
            **kwargs: Additional Table arguments (override defaults)

        Returns:
            Configured Rich Table instance
        """
        defaults = {
            'box': box.SIMPLE,
            'show_header': True,
            'expand': True,
            'padding': (0, 0),
            'collapse_padding': True
        }
        defaults.update(kwargs)

        table = Table(border_style=border_style, **defaults)

        if columns:
            for col_name, col_kwargs in columns:
                table.add_column(col_name, **col_kwargs)

        return table

    @staticmethod
    def create_panel(
        content: Any,
        title: str,
        border_style: str = "magenta",
        **kwargs
    ) -> Panel:
        """Create panel with standard styling.

        Args:
            content: Panel content (Table, Text, or other renderable)
            title: Panel title text
            border_style: Color for panel border
            **kwargs: Additional Panel arguments (override defaults)

        Returns:
            Configured Rich Panel instance
        """
        defaults = {
            'padding': (0, 0),
            'box': box.SIMPLE
        }
        defaults.update(kwargs)

        return Panel(
            content,
            title=f"[{border_style}]{title}[/{border_style}]",
            border_style=border_style,
            **defaults
        )
