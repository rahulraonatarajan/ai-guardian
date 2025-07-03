#!/usr/bin/env python3
"""
NoAI Guardian + FixBot · Rahul Rao Natarajan
Scans a project for AI-opt-out directives, can auto-patch & stage fixes,
and produces a **detailed** GitHub-Actions summary with failure reasons.

Contact · rahulraonatarajan@gmail.com
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

META_TAG = '<meta name="robots" content="noai, noimageai">'

AI_BOTS = [
    "GPTBot",
    "Google-Extended",
    "Anthropic",
    "ClaudeBot",
    "PerplexityBot",
    "CCBot",
    "aiCrawler",
]

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def find_html(root: Path) -> List[Path]:
    """Return recursive list of *.html / *.htm files."""
    return [p for p in root.rglob("*") if p.suffix.lower() in {".html", ".htm"}]


def patch_html(path: Path, fix: bool) -> Tuple[bool, str]:
    """Return (passed, reason). On --fix will inject META_TAG if missing."""
    text = path.read_text("utf-8", "ignore")
    if META_TAG.lower() in text.lower():
        return True, ""

    if not fix:
        return False, "meta tag missing"

    # Try to insert meta tag after first <head>
    patched, n = re.subn(r"(<head[^>]*>)", r"\1\n  " + META_TAG, text, 1, flags=re.I)
    if n:
        path.write_text(patched, "utf-8")
        return True, ""
    return False, "<head> tag not found; cannot inject meta"


def patch_robots(root: Path, fix: bool) -> Tuple[bool, str]:
    """Ensure robots.txt blocks all AI_BOTS. Return (passed, reason)."""
    robots = root / "robots.txt"
    content = robots.read_text("utf-8", "ignore") if robots.exists() else ""
    missing = [b for b in AI_BOTS if b.lower() not in content.lower()]

    if not missing:
        return True, ""

    if not fix:
        return False, f"missing bot rule(s): {', '.join(missing)}"

    # Append rules only for the bots that are missing
    lines = [f"User-agent: {b}\nDisallow: /" for b in missing]
    robots.write_text(content.rstrip() + "\n" + "\n".join(lines) + "\n", "utf-8")
    return True, ""


def write_job_summary(results: Dict[str, Tuple[bool, str]]) -> None:
    """Render a Markdown checklist with failure reasons into Job Summary."""
    summary = ["## NoAI Guardian Report", ""]
    for file_name, (passed, reason) in results.items():
        emoji = "✅" if passed else "❌"
        if passed:
            summary.append(f"- {emoji} **{file_name}**")
        else:
            summary.append(f"- {emoji} **{file_name}** — {reason}")
    summary.append("")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        Path(summary_path).write_text("\n".join(summary), "utf-8")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main() -> None:
    # Clean out any empty args the runner might inject
    sys.argv = [a for a in sys.argv if a.strip()]

    parser = argparse.ArgumentParser(description="Audit / auto-fix AI opt-out rules")
    parser.add_argument("--path", default=".", help="Folder to scan")
    parser.add_argument("--fix", action="store_true", help="Auto-patch violations")
    args = parser.parse_args()

    root = Path(args.path).resolve()

    detailed_results: Dict[str, Tuple[bool, str]] = {}
    all_ok = True

    # ----- HTML pass -----
    for html_file in find_html(root):
        passed, reason = patch_html(html_file, args.fix)
        detailed_results[str(html_file.relative_to(root))] = (passed, reason)
        all_ok &= passed

    # ----- robots.txt -----
    robots_passed, robots_reason = patch_robots(root, args.fix)
    detailed_results["robots.txt"] = (robots_passed, robots_reason)
    all_ok &= robots_passed

    # ----- JSON report for logs / API -----
    json_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": all_ok,
        "details": {
            f: {"passed": res[0], "reason": res[1]} for f, res in detailed_results.items()
        },
    }
    print(json.dumps(json_report, indent=2))

    # ----- Job Summary for GitHub UI -----
    write_job_summary(detailed_results)

    # ----- Stage fixes (if requested) -----
    if args.fix:
        subprocess.run(["git", "add", "."], check=False)

    # Fail CI if anything still non-compliant
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
