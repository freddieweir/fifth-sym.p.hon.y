#!/usr/bin/env python3
"""Workspace Maid - Automated directory organization with preview mode.

Features:
- Markdown file organization by category
- .DS_Store cleanup
- Old .processed/ file archiving
- Deep mode: duplicate detection, stale TODOs
- Git integration: branch creation, commits, PR creation
"""

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Dynamic path resolution for ai-bedo repository
ALBEDO_ROOT = Path(os.getenv("ALBEDO_ROOT", Path.home() / "git" / "internal" / "repos" / "ai-bedo"))


def is_vm_environment() -> bool:
    """Detect if running in VM environment (elevated permissions)."""
    cwd = str(Path.cwd())
    return "/Volumes/" in cwd or "fweirvm" in cwd or "/Users/fweirvm" in cwd


def run_command(cmd: str, args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run a CLI command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [cmd] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    return run_command("git", args, cwd)


def run_gh(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run a gh command and return (returncode, stdout, stderr)."""
    return run_command("gh", args, cwd)


def format_file_size(size: int) -> str:
    """Format size in human-readable form."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


@dataclass
class FileMatch:
    """A file matched to a category."""

    path: Path
    category: str
    destination: str
    size: int
    suggest_review: bool = False

    @property
    def size_human(self) -> str:
        """Human-readable file size."""
        return format_file_size(self.size)


@dataclass
class OrganizationPlan:
    """Complete plan for organizing a directory."""

    target_dir: Path
    matches: list[FileMatch] = field(default_factory=list)
    protected: list[Path] = field(default_factory=list)
    ds_store_files: list[Path] = field(default_factory=list)
    old_processed: list[Path] = field(default_factory=list)
    duplicates: dict[str, list[Path]] = field(default_factory=dict)
    stale_todos: list[tuple[Path, int, str]] = field(default_factory=list)

    def by_destination(self) -> dict[str, list[FileMatch]]:
        """Group matches by destination."""
        result: dict[str, list[FileMatch]] = {}
        for match in self.matches:
            dest = match.destination
            if dest not in result:
                result[dest] = []
            result[dest].append(match)
        return result

    def total_size(self) -> int:
        """Total size of files to move."""
        return sum(m.size for m in self.matches)


class WorkspaceMaid:
    """Organize directory files based on categorization rules."""

    # Protected files - NEVER move these
    PROTECTED_FILES: set[str] = {
        "README.md",
        "CLAUDE.md",
        ".gitignore",
        ".env",
        ".env.example",
        "package.json",
        "package-lock.json",
        "pyproject.toml",
        "uv.lock",
        "Makefile",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "tsconfig.json",
        "astro.config.mjs",
        "LICENSE",
        "LICENSE.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
    }

    # Categories in priority order (first match wins)
    CATEGORIES: list[dict] = [
        {
            "name": "session_summaries",
            "patterns": [
                "PHASE-*.md",
                "PHASE*.md",
                "SESSION-*.md",
                "*-SUMMARY.md",
                "*-SESSION.md",
                "IMPLEMENTATION-*.md",
            ],
            "destination": ".archived/",
            "description": "Session and phase summaries",
        },
        {
            "name": "progress",
            "patterns": ["PROGRESS.md", "*-PROGRESS.md", "HISTORY.md"],
            "destination": ".archived/",
            "description": "Progress tracking files",
        },
        {
            "name": "security_deployment",
            "patterns": [
                "SECURITY-*.md",
                "DEPLOYMENT-*.md",
                "*-DEPLOYMENT.md",
                "*-SECURITY.md",
            ],
            "destination": ".archived/",
            "description": "One-off deployment and security notes",
        },
        {
            "name": "tasks",
            "patterns": ["TODO.md", "TODO-*.md", "TASK-*.md", "TASKS.md"],
            "destination": "tasks/",
            "description": "Task and TODO tracking",
        },
        {
            "name": "docs",
            "patterns": [
                "QUICKSTART.md",
                "SETUP.md",
                "INSTALL.md",
                "GETTING-STARTED.md",
                "USAGE.md",
                "API.md",
                "ARCHITECTURE.md",
            ],
            "destination": "docs/",
            "description": "Documentation files",
        },
        {
            "name": "misc",
            "patterns": ["*.md"],
            "destination": "docs/misc/",
            "description": "Uncategorized markdown (review recommended)",
            "suggest_review": True,
            "gitignore": True,
        },
    ]

    # Directories to exclude from scanning
    EXCLUDE_DIRS: set[str] = {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        "dist",
        "build",
        ".archived",
        ".processed",
        "docs",
        "tasks",
    }

    def __init__(
        self,
        target_dir: Path,
        quiet: bool = False,
        deep: bool = False,
    ):
        self.target_dir = target_dir.resolve()
        self.quiet = quiet
        self.deep = deep
        self.log_file = self.target_dir / ".maid-log.json"

    def analyze(self) -> OrganizationPlan:
        """Analyze directory and create organization plan."""
        plan = OrganizationPlan(target_dir=self.target_dir)

        # Scan for .DS_Store files (recursive)
        plan.ds_store_files = list(self.target_dir.rglob(".DS_Store"))

        # Scan for old .processed files
        processed_dir = self.target_dir / ".processed"
        if processed_dir.exists():
            threshold = datetime.now() - timedelta(days=30)
            for f in processed_dir.iterdir():
                if f.is_file():
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    if mtime < threshold:
                        plan.old_processed.append(f)

        # Get markdown files in root directory only
        md_files = [f for f in self.target_dir.iterdir() if f.is_file() and f.suffix == ".md"]

        for file_path in md_files:
            filename = file_path.name

            # Check if protected
            if filename in self.PROTECTED_FILES:
                plan.protected.append(file_path)
                continue

            # Match against categories in order
            matched = False
            for category in self.CATEGORIES:
                if self._matches_patterns(filename, category["patterns"]):
                    plan.matches.append(
                        FileMatch(
                            path=file_path,
                            category=category["name"],
                            destination=category["destination"],
                            size=file_path.stat().st_size,
                            suggest_review=category.get("suggest_review", False),
                        )
                    )
                    matched = True
                    break

            # Should not reach here due to *.md catch-all, but just in case
            if not matched:
                plan.protected.append(file_path)

        # Deep analysis
        if self.deep:
            plan.duplicates = self._find_duplicates()
            plan.stale_todos = self._find_stale_todos()

        return plan

    def _matches_patterns(self, filename: str, patterns: list[str]) -> bool:
        """Check if filename matches any pattern."""
        for pattern in patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False

    def _find_duplicates(self) -> dict[str, list[Path]]:
        """Find duplicate files by MD5 hash."""
        hashes: dict[str, list[Path]] = {}

        for f in self.target_dir.rglob("*"):
            if f.is_file() and not any(p in f.parts for p in self.EXCLUDE_DIRS):
                try:
                    with open(f, "rb") as fh:
                        h = hashlib.md5(fh.read()).hexdigest()
                    if h not in hashes:
                        hashes[h] = []
                    hashes[h].append(f)
                except (OSError, PermissionError):
                    pass

        # Return only duplicates
        return {h: paths for h, paths in hashes.items() if len(paths) > 1}

    def _find_stale_todos(self) -> list[tuple[Path, int, str]]:
        """Find TODO comments in code files."""
        todos = []
        extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".go", ".rs"}

        for f in self.target_dir.rglob("*"):
            if f.is_file() and f.suffix in extensions:
                if any(p in f.parts for p in self.EXCLUDE_DIRS):
                    continue
                try:
                    with open(f, encoding="utf-8", errors="ignore") as fh:
                        for i, line in enumerate(fh, 1):
                            if "TODO" in line or "FIXME" in line:
                                todos.append((f, i, line.strip()[:80]))
                except (OSError, PermissionError):
                    pass

        return todos[:50]  # Limit to 50

    def execute(self, plan: OrganizationPlan, dry_run: bool = True) -> dict:
        """Execute the organization plan."""
        results = {
            "moved": [],
            "deleted": [],
            "created_dirs": [],
            "gitignore_updated": False,
            "errors": [],
            "timestamp": datetime.now().isoformat(),
        }

        if dry_run:
            return results

        # Delete .DS_Store files
        for ds in plan.ds_store_files:
            try:
                ds.unlink()
                results["deleted"].append(str(ds))
            except OSError as e:
                results["errors"].append({"file": str(ds), "error": str(e)})

        # Group moves by destination
        by_dest = plan.by_destination()
        needs_gitignore = False

        for destination, matches in by_dest.items():
            dest_path = self.target_dir / destination

            # Create destination directory
            if not dest_path.exists():
                dest_path.mkdir(parents=True)
                results["created_dirs"].append(str(dest_path))

            # Check if this category needs gitignore
            for cat in self.CATEGORIES:
                if cat["destination"] == destination and cat.get("gitignore"):
                    needs_gitignore = True

            # Move files
            for match in matches:
                try:
                    new_path = dest_path / match.path.name
                    shutil.move(str(match.path), str(new_path))
                    results["moved"].append(
                        {
                            "from": str(match.path),
                            "to": str(new_path),
                            "category": match.category,
                            "size": match.size,
                        }
                    )
                except OSError as e:
                    results["errors"].append({"file": str(match.path), "error": str(e)})

        # Update .gitignore if needed
        if needs_gitignore:
            self._update_gitignore("docs/misc/")
            results["gitignore_updated"] = True

        # Archive old processed files
        if plan.old_processed:
            archive_dir = self.target_dir / ".processed" / "archived"
            archive_dir.mkdir(parents=True, exist_ok=True)
            for f in plan.old_processed:
                try:
                    shutil.move(str(f), str(archive_dir / f.name))
                    results["moved"].append(
                        {"from": str(f), "to": str(archive_dir / f.name), "category": "old_processed", "size": 0}
                    )
                except OSError as e:
                    results["errors"].append({"file": str(f), "error": str(e)})

        # Write log
        self._write_log(results)

        return results

    def _update_gitignore(self, path: str):
        """Add path to .gitignore if not present."""
        gitignore = self.target_dir / ".gitignore"
        lines = []

        if gitignore.exists():
            lines = gitignore.read_text().splitlines()

        if path not in lines and f"/{path}" not in lines:
            lines.append(f"\n# Uncategorized markdown (maid cleanup)")
            lines.append(path)
            gitignore.write_text("\n".join(lines) + "\n")

    def _write_log(self, results: dict):
        """Write operation log for audit."""
        log_data = []
        if self.log_file.exists():
            try:
                log_data = json.loads(self.log_file.read_text())
            except json.JSONDecodeError:
                pass

        log_data.append(results)

        self.log_file.write_text(json.dumps(log_data, indent=2))

    def print_plan(self, plan: OrganizationPlan, execute: bool = False):
        """Print the organization plan."""
        if not self.quiet:
            print("\u2554" + "\u2550" * 50 + "\u2557")
            print("\u2551       Workspace Maid" + " " * 29 + "\u2551")
            print("\u255a" + "\u2550" * 50 + "\u255d")
            print()

        mode = "Execute" if execute else "Preview (use --execute to apply)"
        print(f"Target: {self.target_dir}")
        print(f"Mode: {mode}")
        print()

        # .DS_Store files
        if plan.ds_store_files:
            print(f"[DS_STORE] {len(plan.ds_store_files)} files to delete")
            if not self.quiet:
                for f in plan.ds_store_files[:5]:
                    print(f"  {f.relative_to(self.target_dir)}")
                if len(plan.ds_store_files) > 5:
                    print(f"  ... and {len(plan.ds_store_files) - 5} more")
            print()

        # Old processed files
        if plan.old_processed:
            print(f"[PROCESSED] {len(plan.old_processed)} old files to archive (30+ days)")
            print()

        # Markdown organization
        by_dest = plan.by_destination()
        for destination, matches in sorted(by_dest.items()):
            label = destination.upper().replace("/", "").replace(".", "")
            review_note = ""
            if any(m.suggest_review for m in matches):
                review_note = " (review recommended)"

            print(f"[{label}] \u2192 {destination}{review_note}")
            for match in sorted(matches, key=lambda m: m.path.name):
                print(f"  {match.path.name} ({match.size_human})")
            print()

        # Protected files
        if plan.protected:
            print("[KEEP] (protected files)")
            for path in sorted(plan.protected):
                print(f"  {path.name}")
            print()

        # Deep analysis results
        if self.deep:
            if plan.duplicates:
                print(f"[DUPLICATES] {len(plan.duplicates)} sets of duplicate files")
                if not self.quiet:
                    for h, paths in list(plan.duplicates.items())[:3]:
                        print(f"  Hash {h[:8]}:")
                        for p in paths:
                            print(f"    {p.relative_to(self.target_dir)}")
                print()

            if plan.stale_todos:
                print(f"[TODOS] {len(plan.stale_todos)} TODO/FIXME comments found")
                if not self.quiet:
                    for path, line, text in plan.stale_todos[:5]:
                        print(f"  {path.relative_to(self.target_dir)}:{line}")
                        print(f"    {text[:60]}...")
                print()

        # Summary
        total_move = len(plan.matches)
        total_delete = len(plan.ds_store_files)

        print("Summary:")
        if total_delete:
            print(f"  .DS_Store to delete: {total_delete}")
        if plan.old_processed:
            print(f"  Old .processed to archive: {len(plan.old_processed)}")

        for dest, matches in by_dest.items():
            dest_size = sum(m.size for m in matches)
            print(f"  Files to {dest}: {len(matches)} ({self._format_size(dest_size)})")

        print(f"  Files protected: {len(plan.protected)}")

        if not execute:
            print()
            print("Run with --execute to apply changes.")

    def _format_size(self, size: int) -> str:
        """Format size in human-readable form."""
        return format_file_size(size)

    def write_audio_summary(self, results: dict, pr_url: str = ""):
        """Write audio summary file."""
        moved_count = len(results.get("moved", []))
        deleted_count = len(results.get("deleted", []))

        if not moved_count and not deleted_count:
            return

        # Determine audio directory
        audio_dir = ALBEDO_ROOT / "communications" / "audio"

        if not audio_dir.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        audio_file = audio_dir / f"{timestamp}-maid.txt"

        parts = []
        if moved_count:
            parts.append(f"{moved_count} files organized")
        if deleted_count:
            parts.append(f"{deleted_count} DS_Store files removed")

        summary = "Workspace cleanup complete. " + ", ".join(parts) + "."
        if pr_url:
            summary += " Pull request created for your review."
        audio_file.write_text(summary)

    def is_git_repo(self) -> bool:
        """Check if target directory is a git repository."""
        code, _, _ = run_git(["rev-parse", "--git-dir"], self.target_dir)
        return code == 0

    def get_current_branch(self) -> str:
        """Get current git branch name."""
        code, stdout, _ = run_git(["branch", "--show-current"], self.target_dir)
        return stdout if code == 0 else ""

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        code, stdout, _ = run_git(["status", "--porcelain"], self.target_dir)
        return bool(stdout)

    def create_branch(self, branch_name: str) -> bool:
        """Create and checkout a new branch."""
        code, _, stderr = run_git(["checkout", "-b", branch_name], self.target_dir)
        if code != 0:
            print(f"  Error creating branch: {stderr}", file=sys.stderr)
            return False
        return True

    def commit_changes(self, results: dict) -> bool:
        """Stage and commit all changes."""
        # Stage all changes
        code, _, stderr = run_git(["add", "-A"], self.target_dir)
        if code != 0:
            print(f"  Error staging changes: {stderr}", file=sys.stderr)
            return False

        # Build commit message
        moved_count = len(results.get("moved", []))
        deleted_count = len(results.get("deleted", []))

        parts = []
        if moved_count:
            parts.append(f"{moved_count} files organized")
        if deleted_count:
            parts.append(f"{deleted_count} .DS_Store files removed")

        summary = ", ".join(parts)

        # Get destination breakdown
        by_dest: dict[str, int] = {}
        for m in results.get("moved", []):
            dest = m.get("category", "unknown")
            by_dest[dest] = by_dest.get(dest, 0) + 1

        body_lines = ["", "Changes:"]
        for dest, count in sorted(by_dest.items()):
            body_lines.append(f"- {dest}: {count} files")
        if deleted_count:
            body_lines.append(f"- .DS_Store: {deleted_count} files deleted")
        if results.get("gitignore_updated"):
            body_lines.append("- .gitignore: updated with docs/misc/")

        commit_msg = f"chore: workspace cleanup - {summary}" + "\n".join(body_lines)

        code, _, stderr = run_git(["commit", "-m", commit_msg], self.target_dir)
        if code != 0:
            print(f"  Error committing: {stderr}", file=sys.stderr)
            return False
        return True

    def push_branch(self, branch_name: str) -> bool:
        """Push branch to remote."""
        code, _, stderr = run_git(["push", "-u", "origin", branch_name], self.target_dir)
        if code != 0:
            print(f"  Error pushing branch: {stderr}", file=sys.stderr)
            return False
        return True

    def create_pr(self, results: dict) -> str:
        """Create a pull request and return the URL."""
        moved_count = len(results.get("moved", []))
        deleted_count = len(results.get("deleted", []))

        # Build PR title
        parts = []
        if moved_count:
            parts.append(f"{moved_count} files organized")
        if deleted_count:
            parts.append(f"{deleted_count} .DS_Store removed")
        title = f"chore: workspace cleanup - {', '.join(parts)}"

        # Build PR body
        by_dest: dict[str, list[str]] = {}
        for m in results.get("moved", []):
            cat = m.get("category", "unknown")
            filename = Path(m.get("from", "")).name
            if cat not in by_dest:
                by_dest[cat] = []
            by_dest[cat].append(filename)

        body_lines = [
            "## Summary",
            "",
            "Automated workspace cleanup via `/maid` command.",
            "",
            "## Changes",
            "",
        ]

        for cat, files in sorted(by_dest.items()):
            body_lines.append(f"### {cat.replace('_', ' ').title()}")
            for f in files[:10]:
                body_lines.append(f"- {f}")
            if len(files) > 10:
                body_lines.append(f"- ... and {len(files) - 10} more")
            body_lines.append("")

        if deleted_count:
            body_lines.append(f"### Cleanup")
            body_lines.append(f"- Removed {deleted_count} .DS_Store files")
            body_lines.append("")

        if results.get("gitignore_updated"):
            body_lines.append("### Config")
            body_lines.append("- Added `docs/misc/` to .gitignore")
            body_lines.append("")

        body = "\n".join(body_lines)

        code, stdout, stderr = run_gh(
            ["pr", "create", "--title", title, "--body", body],
            self.target_dir,
        )

        if code != 0:
            print(f"  Error creating PR: {stderr}", file=sys.stderr)
            return ""

        # stdout contains the PR URL
        return stdout


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Workspace Maid - Automated directory organization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  workspace_maid.py                    # Preview current directory
  workspace_maid.py --execute          # Execute cleanup
  workspace_maid.py --commit           # Execute + create branch + commit
  workspace_maid.py --pr               # Execute + commit + create PR
  workspace_maid.py --path /some/dir   # Target specific directory
  workspace_maid.py --deep             # Include duplicate/TODO analysis
        """,
    )
    parser.add_argument(
        "--path",
        "-p",
        type=Path,
        default=Path.cwd(),
        help="Target directory to organize (default: current directory)",
    )
    parser.add_argument(
        "--execute",
        "-e",
        action="store_true",
        help="Execute the organization (default: preview only)",
    )
    parser.add_argument(
        "--commit",
        "-c",
        action="store_true",
        help="Create branch and commit changes (implies --execute)",
    )
    parser.add_argument(
        "--pr",
        action="store_true",
        help="Create PR after committing (implies --commit)",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Include duplicate detection and stale TODO analysis",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Minimal output",
    )

    args = parser.parse_args()

    # Resolve path
    target = args.path.resolve()
    if not target.is_dir():
        print(f"Error: {target} is not a directory", file=sys.stderr)
        return 1

    # Flag implications: --pr implies --commit, --commit implies --execute
    if args.pr:
        args.commit = True
    if args.commit:
        args.execute = True

    # Run maid
    maid = WorkspaceMaid(target, quiet=args.quiet, deep=args.deep)
    plan = maid.analyze()

    # Print plan
    maid.print_plan(plan, args.execute)

    # Check if there's anything to do
    has_changes = bool(plan.matches) or bool(plan.ds_store_files) or bool(plan.old_processed)
    if not has_changes:
        print()
        print("Nothing to clean up!")
        return 0

    # Git preconditions for --commit/--pr
    if args.commit:
        if not maid.is_git_repo():
            print(f"Error: {target} is not a git repository", file=sys.stderr)
            return 1

        if maid.has_uncommitted_changes():
            print("Error: Repository has uncommitted changes. Please commit or stash first.", file=sys.stderr)
            return 1

    # Execute if requested
    if args.execute:
        print()

        # Create branch if committing
        branch_name = ""
        original_branch = ""
        if args.commit:
            original_branch = maid.get_current_branch()
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            branch_name = f"chore/maid-cleanup-{timestamp}"

            print(f"Creating branch: {branch_name}")
            if not maid.create_branch(branch_name):
                return 1

        print("Executing...")
        results = maid.execute(plan, dry_run=False)

        moved = len(results.get("moved", []))
        deleted = len(results.get("deleted", []))

        if moved or deleted:
            if moved:
                print(f"\u2713 Moved {moved} files")
            if deleted:
                print(f"\u2713 Deleted {deleted} .DS_Store files")
            if results.get("gitignore_updated"):
                print("\u2713 Updated .gitignore")

        if results.get("errors"):
            print(f"\u2717 {len(results['errors'])} errors occurred")
            for err in results["errors"]:
                print(f"  - {err['file']}: {err['error']}")
            return 1

        # Commit if requested
        pr_url = ""
        if args.commit and (moved or deleted):
            print()
            print("Committing changes...")
            if not maid.commit_changes(results):
                return 1
            print("\u2713 Changes committed")

            # Create PR if requested
            if args.pr:
                print()
                print("Pushing branch...")
                if not maid.push_branch(branch_name):
                    return 1
                print("\u2713 Branch pushed")

                print("Creating pull request...")
                pr_url = maid.create_pr(results)
                if pr_url:
                    print(f"\u2713 PR created: {pr_url}")
                else:
                    print("\u2717 Failed to create PR")
                    return 1

        # Audio summary
        if moved or deleted:
            maid.write_audio_summary(results, pr_url)

    return 0


if __name__ == "__main__":
    sys.exit(main())
