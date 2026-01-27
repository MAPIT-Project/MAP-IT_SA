#!/usr/bin/env python3
"""
Script to convert print() statements to proper logging calls.
Run with --dry-run first to preview changes.
"""

import re
import sys
from pathlib import Path

# Mapping of emoji/prefix patterns to log levels
LOG_LEVEL_PATTERNS = [
    # Error patterns
    (r"❌|Error|ERROR|Failed|FAILED|failed", "error"),
    (r"⚠️|Warning|WARNING|warn|Could not|Skipping", "warning"),
    # Debug patterns
    (r"DEBUG|🔬", "debug"),
    # Info patterns (default)
    (r"✅|🎯|📞|🔍|📊|🎉|💾|📡|🔄|📈|🔗|✅|🟢|🔵|🟡|💡|🔧|📂|🚗|📋|🔜|🌐", "info"),
]


def determine_log_level(content: str) -> str:
    """Determine the appropriate log level based on print content."""
    for pattern, level in LOG_LEVEL_PATTERNS:
        if re.search(pattern, content):
            return level
    return "info"  # Default to info


def clean_emoji_prefix(content: str) -> str:
    """Remove emoji prefixes that are redundant with log levels."""
    # Remove common emoji prefixes (keep them for now, just strip leading/trailing)
    return content.strip()


def convert_print_to_log(line: str, indent: str = "") -> str:
    """Convert a print statement to a logging call."""
    # Match print("...") or print(f"...")
    match = re.match(r'^(\s*)print\((f?".*")\)$', line)
    if not match:
        match = re.match(r"^(\s*)print\((f?\'.*\')\)$", line)
    if not match:
        # Handle multi-line or complex prints
        match = re.match(r"^(\s*)print\((.+)\)$", line)

    if not match:
        return None

    current_indent = match.group(1)
    content = match.group(2)

    # Determine log level
    level = determine_log_level(content)

    # Return the converted line
    return f"{current_indent}logger.{level}({content})"


def process_file(filepath: Path, dry_run: bool = True) -> tuple[int, list[str]]:
    """Process a single file and convert print statements."""
    changes = []

    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    has_logging_import = False
    has_logger = False

    for line in lines:
        if "import logging" in line:
            has_logging_import = True
        if "logger = logging.getLogger" in line:
            has_logger = True

        if line.strip().startswith("print("):
            converted = convert_print_to_log(line.rstrip())
            if converted:
                changes.append(f"  {line.rstrip()} -> {converted.strip()}")
                new_lines.append(converted + "\n")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Add logging import if needed and we made changes
    if changes and not has_logging_import:
        # Find first import or top of file
        for i, line in enumerate(new_lines):
            if line.startswith("import ") or line.startswith("from "):
                new_lines.insert(i, "import logging\n")
                break
        else:
            new_lines.insert(0, "import logging\n")
        changes.insert(0, "  + Added: import logging")

    if changes and not has_logger:
        # Add logger after imports
        for i, line in enumerate(new_lines):
            if (
                line.strip()
                and not line.startswith("import ")
                and not line.startswith("from ")
                and not line.startswith("#")
            ):
                new_lines.insert(i, "\nlogger = logging.getLogger(__name__)\n")
                break
        changes.insert(
            0 if "import logging" not in str(changes) else 1,
            "  + Added: logger = logging.getLogger(__name__)",
        )

    if not dry_run and changes:
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    return len([c for c in changes if c.startswith("  print")]), changes


def main():
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    # Services directory
    services_dir = Path(__file__).parent.parent / "app" / "services"

    if not services_dir.exists():
        print(f"Services directory not found: {services_dir}")
        sys.exit(1)

    print(f"{'[DRY RUN] ' if dry_run else ''}Converting print statements in {services_dir}")
    print("=" * 80)

    total_changes = 0
    files_changed = 0

    for filepath in services_dir.rglob("*.py"):
        count, changes = process_file(filepath, dry_run)
        if changes:
            print(f"\n{filepath.relative_to(services_dir)}:")
            for change in changes[:10]:  # Show first 10 changes
                print(change)
            if len(changes) > 10:
                print(f"  ... and {len(changes) - 10} more changes")
            total_changes += count
            files_changed += 1

    print("\n" + "=" * 80)
    print(f"Total: {total_changes} print statements in {files_changed} files")
    if dry_run:
        print("Run without --dry-run to apply changes")


if __name__ == "__main__":
    main()
