#!/usr/bin/env python3
"""
NoAI Guardian + FixBot · Rahul Rao Natarajan
Audits a repo for AI-opt-out directives, optionally patches them,
and produces a **human-friendly table** in the GitHub-Actions Job Summary:

| File | Status | Reason | Fix (what & where) |

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
    """Return *.html / *.htm files under root."""
    return [p for p in root.rglob("*") if p.suffix.lower() in {".html", ".htm"}]


def patch_html(path: Path, fix: bool) -> Tuple[bool, str, str]:
    """
    Make sure file contains META_TAG.
    Returns (passed, reason, fix_snippet).
    """
    text = path.read_text("utf-8", "ignore")
    if META_TAG.lower() in text.lower():
        return True, "", ""

    if not fix:
        return False, "meta tag missing", META_TAG

    patched, n = re.subn(r"(<head[^>]*>)", r"\1\n  " + META_TAG, text, 1, flags=re.I)
    if n:
        path.write_text(patched, "utf-8")
        return True, "", ""
    return False, "<head> tag not found", META_TAG


def patch_robots(root: Path, fix: bool) -> Tuple[bool, str, str]:
    """
    Ensure robots.txt blocks all AI_BOTS.
    Returns (passed, reason, fix_snippet).
    """
    robots = root / "robots.txt"
    content = robots.read_text("utf-8", "ignore") if robots.exists() else ""
    missing = [b for b in AI_BOTS if b.lower() not in content.lower()]

    if not missing:
        return True, "", ""

    snippet = "\n".join(f"User-agent: {b}\nDisallow: /" for b in missing)

    if not fix:
        return False, f"missing bot rule(s): {', '.join(missing)}", snippet

    robots.write_text(content.rstrip() + "\n" + snippet + "\n", "utf-8")
    return True, "", ""


def write_job_summary(results: Dict[str, Dict[str, str]]) -> None:
    """
    Render a Markdown table (no collapsible blocks) with explicit fix guidance.
    """
    summary = [
        "## NoAI Guardian Report",
        "",
        "| File | Status | Reason | Fix <br>(what & where) |",
        "|------|--------|--------|------------------------|",
    ]

    for fname, data in results.items():
        status = "✅ Pass" if data["passed"] else "❌ Fail"
        reason = data["reason"] or "—"

        # Build fix cell
        if data["passed"]:
            fix_cell = "—"
        elif fname == "robots.txt":
            fix_cell = f"Add to **/robots.txt**:<br>`{data['fix'].strip().replace(chr(10), ' ; ')}`"
        else:
            fix_cell = (
                f"Insert inside `<head>` of **{fname}**:<br>"
                f"`{META_TAG}`"
            )

        summary.append(f"| **{fname}** | {status} | {reason} | {fix_cell} |")

    summary.append("")  # trailing newline

    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        Path(path).write_text("\n".join(summary), "utf-8")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main() -> None:
    # Remove blank arguments that GitHub could inject
    sys.argv = [a for a in sys.argv if a.strip()]

    parser = argparse.ArgumentParser(description="Audit / auto-fix AI opt-out rules")
    parser.add_argument("--path", default=".", help="Folder to scan")
    parser.add_argument("--fix", action="store_true", help="Auto-patch violations")
    args = parser.parse_args()

    root = Path(args.path).resolve()

    # results[file] = {passed, reason, fix}
    results: Dict[str, Dict[str, str]] = {}
    all_ok = True

    # ---- HTML files ----
    for html_file in find_html(root):
        passed, reason, snippet = patch_html(html_file, args.fix)
        results[str(html_file.relative_to(root))] = {
            "passed": passed,
            "reason": reason,
            "fix": snippet,
        }
        all_ok &= passed

    # ---- robots.txt ----
    rob_pass, rob_reason, rob_snip = patch_robots(root, args.fix)
    results["robots.txt"] = {"passed": rob_pass, "reason": rob_reason, "fix": rob_snip}
    all_ok &= rob_pass

    # ---- JSON log ----
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

    # ---- Markdown summary ----
    write_job_summary(results)

    # ---- git add when fixes applied ----
    if args.fix:
        subprocess.run(["git", "add", "."], check=False)

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
