"""Documentation browser panel for quick access to markdown files."""

import subprocess
from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.widgets import DataTable, Static


class DocumentationPanel(Static):
    """Browse and open documentation files."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.doc_files = []
        self.git_root = Path.home() / "git"

    def compose(self) -> ComposeResult:
        """Create the documentation browser panel."""
        yield Static("Documentation", classes="panel-title")
        table = DataTable(id="docs-table")
        table.add_columns("Type", "Name", "Location")
        table.cursor_type = "row"
        yield table

    def on_mount(self) -> None:
        """Index documentation files on mount."""
        self.index_documentation()
        self.populate_table()

    def index_documentation(self):
        """Index all documentation files from various locations."""
        self.doc_files = []

        # 1. Official documentation directory
        official_docs = Path.home() / "git" / "documentation"
        if official_docs.exists():
            for md_file in official_docs.rglob("*.md"):
                self.doc_files.append({
                    "type": "📚 Official",
                    "name": md_file.stem,
                    "location": self._relative_path(md_file),
                    "path": md_file
                })

        # 2. Repo-specific documentation patterns
        doc_patterns = [
            "**/CLAUDE.md",
            "**/README.md",
            "**/docs/**/*.md",
            "**/tasks/**/*.md",
            "**/todos/**/*.md",
            "**/blueprints/**/*.md",
            "**/notes/**/*.md",
        ]

        for pattern in doc_patterns:
            for md_file in self.git_root.glob(pattern):
                # Skip if already indexed
                if any(d["path"] == md_file for d in self.doc_files):
                    continue

                # Determine type
                if md_file.name == "CLAUDE.md":
                    doc_type = "🤖 Claude"
                elif md_file.name == "README.md":
                    doc_type = "📖 README"
                elif "/docs/" in str(md_file):
                    doc_type = "📄 Docs"
                elif "/tasks/" in str(md_file):
                    doc_type = "📋 Task"
                elif "/todos/" in str(md_file):
                    doc_type = "✓ TODO"
                elif "/blueprints/" in str(md_file):
                    doc_type = "🏗️ Blueprint"
                elif "/notes/" in str(md_file):
                    doc_type = "📝 Note"
                else:
                    doc_type = "📄 Doc"

                self.doc_files.append({
                    "type": doc_type,
                    "name": md_file.stem,
                    "location": self._relative_path(md_file),
                    "path": md_file
                })

        # Sort by type, then name
        self.doc_files.sort(key=lambda x: (x["type"], x["name"]))

        # Limit to most recent 30 for performance (prevent rendering issues)
        self.doc_files = self.doc_files[:30]

    def _relative_path(self, filepath: Path) -> str:
        """Get relative path from git root."""
        try:
            return str(filepath.relative_to(self.git_root))
        except ValueError:
            return str(filepath)

    def populate_table(self):
        """Populate the DataTable with documentation files."""
        table = self.query_one("#docs-table", DataTable)
        table.clear()

        if not self.doc_files:
            table.add_row("📄", "No docs found", "--")
            return

        for idx, doc in enumerate(self.doc_files):
            # Don't truncate - let table handle wrapping
            table.add_row(
                doc["type"],
                doc["name"],
                doc["location"],
                key=str(idx)
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - open documentation file."""
        try:
            row_key = event.row_key.value
            idx = int(row_key)
            doc = self.doc_files[idx]

            # Log to activity log
            log = self.app.query_one("#activity-log")
            timestamp = datetime.now().strftime("%H:%M:%S")
            log.write_line(f"[dim][{timestamp}][/dim] Opening: {doc['name']}")

            # Try Apple Notes first, fallback to VSCodium
            success = self.open_in_apple_notes(doc["path"])
            if success:
                log.write_line(f"[green]✓[/green] Imported to Apple Notes: {doc['name']}")
            else:
                # Fallback to VSCodium
                self.open_in_vscodium(doc["path"])
                log.write_line(f"[green]✓[/green] Opened in VSCodium: {doc['name']}")

        except Exception as e:
            log = self.app.query_one("#activity-log")
            log.write_line(f"[red]✗[/red] Error opening doc: {e}")

    def open_in_apple_notes(self, md_path: Path) -> bool:
        """Import markdown file into Apple Notes using AppleScript.

        Returns True if successful, False otherwise.
        """
        applescript_path = (
            Path.home() / "git" / "internal" / "repos" /
            "applescript-arsenal" / "notes" / "import_markdown.applescript"
        )

        if not applescript_path.exists():
            return False

        try:
            result = subprocess.run(
                ["osascript", str(applescript_path), str(md_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def open_in_vscodium(self, md_path: Path):
        """Open markdown file in VSCodium."""
        try:
            subprocess.Popen(
                ["codium", str(md_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            # Try alternative command
            subprocess.Popen(
                ["code", str(md_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    def refresh_data(self):
        """Refresh documentation index."""
        self.index_documentation()
        self.populate_table()
