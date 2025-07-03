#!/usr/bin/env python3                          # Allow direct CLI execution on *nix

"""
NoAI Guardian + FixBot  ·  Rahul Rao Natarajan  # Doc-string header
Scans a project for AI-opt-out directives; can auto-patch and stage fixes.

Contact: rahulraonatarajan@gmail.com
"""

# ---------- Standard-library imports ----------
from __future__ import annotations             # Enable postponed type hints (py≤3.10)

import argparse                                # Parse CLI flags
import json                                    # Emit structured report for logs/CI
import subprocess                              # Stage fixes via git
import sys, re                                 # Argument tweaks / regex inject
from pathlib import Path                       # Path manipulation that respects OS
from typing import List                        # Static typing for lists
from datetime import datetime, timezone        # UTC timestamp for report
import os                                      # Access GITHUB_STEP_SUMMARY

# ---------- Config constants ----------
META_TAG = '<meta name="robots" content="noai, noimageai">'     # Required meta tag
AI_BOTS = [                                                    # AI crawlers to block
    "GPTBot",
    "Google-Extended",
    "Anthropic",
    "ClaudeBot",
    "PerplexityBot",
    "CCBot",
    "aiCrawler",
]

# --------------------------------------------------------------------------- #
# Utility helpers
# --------------------------------------------------------------------------- #

def find_html(root: Path) -> List[Path]:
    """Return all *.html / *.htm files under root (recursive)."""
    return [p for p in root.rglob("*") if p.suffix.lower() in {".html", ".htm"}]


def patch_html(path: Path, fix: bool) -> bool:
    """
    Ensure HTML file contains META_TAG.
    • Returns True if already compliant or successfully patched.
    • Returns False if non-compliant and --fix not set (or patch failed).
    """
    text = path.read_text("utf-8", "ignore")                      # Load file
    if META_TAG.lower() in text.lower():                         # Already ok?
        return True
    if not fix:                                                  # Audit-only run
        return False
    # Inject meta tag right after first <head>
    patched, n = re.subn(                                        # Regex replace
        r"(<head[^>]*>)",                                        # Match opening head
        r"\1\n  " + META_TAG,                                    # Insert tag
        text,
        count=1,
        flags=re.I,
    )
    if n:                                                        # Found <head>
        path.write_text(patched, "utf-8")                        # Save patched file
        return True
    return False                                                 # No <head> to patch


def patch_robots(root: Path, fix: bool) -> bool:
    """
    Ensure robots.txt disallows all AI_BOTS.
    Works for both existing and missing robots.txt.
    """
    robots = root / "robots.txt"                                 # Calculate path
    content = robots.read_text("utf-8", "ignore") if robots.exists() else ""  # Read or empty
    compliant = all(bot.lower() in content.lower() for bot in AI_BOTS)        # Check presence
    if compliant or not fix:                                     # Already okay (or audit-only)
        return compliant
    # Build lines for only the missing bots
    lines = [
        f"User-agent: {bot}\nDisallow: /"
        for bot in AI_BOTS
        if bot.lower() not in content.lower()
    ]
    # Append lines and write back
    robots.write_text(content.rstrip() + "\n" + "\n".join(lines) + "\n", "utf-8")
    return True


def write_job_summary(results: dict[str, bool]) -> None:
    """
    Write a Markdown report to $GITHUB_STEP_SUMMARY so GitHub
    renders a clean checklist in the Actions UI.
    """
    summary = ["## NoAI Guardian Report", ""]                    # Header line
    for fname, passed in results.items():                        # Loop each file
        emoji = "✅" if passed else "❌"                          # Pass/fail indicator
        summary.append(f"- {emoji} **{fname}**")                 # Markdown bullet
    summary.append("")                                           # Final newline
    path = os.environ.get("GITHUB_STEP_SUMMARY")                 # GitHub-provided file path
    if path:
        Path(path).write_text("\n".join(summary), "utf-8")       # Write summary


# --------------------------------------------------------------------------- #
# Main CLI entrypoint
# --------------------------------------------------------------------------- #

def main() -> None:
    # ----- Sanitize argv (GitHub might pass blank args) -----
    sys.argv = [arg for arg in sys.argv if arg.strip()]          # Remove '' entries

    # ----- CLI parsing -----
    parser = argparse.ArgumentParser(description="Audit / auto-fix AI opt-out rules")
    parser.add_argument("--path", default=".", help="Repository folder to scan")
    parser.add_argument("--fix", action="store_true", help="Auto-fix & git-add")
    args = parser.parse_args()

    root = Path(args.path).resolve()                             # Absolute root path

    # ----- Scan HTML -----
    results: dict[str, bool] = {}                                # File → pass/fail
    all_ok = True                                                # Aggregate pass flag
    for html_file in find_html(root):                            # Walk HTML files
        passed = patch_html(html_file, args.fix)                 # Audit / patch
        results[str(html_file.relative_to(root))] = passed       # Store result
        all_ok &= passed                                         # Aggregate AND

    # ----- Scan robots.txt -----
    robots_ok = patch_robots(root, args.fix)                     # Audit / patch
    results["robots.txt"] = robots_ok                            # Store result
    all_ok &= robots_ok                                          # Aggregate AND

    # ----- Emit JSON report -----
    print(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "passed": all_ok,
                "details": results,
            },
            indent=2,
        )
    )

    # ----- Emit human-friendly summary -----
    write_job_summary(results)

    # ----- Stage fixes (if any) -----
    if args.fix:                                                 # Only when --fix
        subprocess.run(["git", "add", "."], check=False)         # Stage all modified files

    # ----- CI exit code -----
    if not all_ok:                                               # Any violation left?
        sys.exit(1)                                              # Fail the job


# Standard Python entrypoint guard
if __name__ == "__main__":
    main()
