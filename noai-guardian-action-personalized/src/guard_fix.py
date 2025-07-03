#!/usr/bin/env python3  # Script entrypoint
"""NoAI Guardian + FixBot (Rahul Rao Natarajan)

Scans HTML files for AI‑opt‑out meta tag and robots.txt for AI crawler blocks.
When run with --fix, missing directives are injected and staged via git.

Contact: rahulraonatarajan@gmail.com
"""
import argparse, json, sys, re, datetime
from pathlib import Path
from typing import List

META_TAG = '<meta name="robots" content="noai, noimageai">'
AI_BOTS = ["GPTBot", "Google-Extended", "Anthropic", "ClaudeBot", "PerplexityBot", "CCBot", "aiCrawler"]

def find_html(root: Path) -> List[Path]:
    return [p for p in root.rglob('*') if p.suffix.lower() in ('.html', '.htm')]

def patch_html(path: Path, fix: bool) -> bool:
    text = path.read_text('utf-8', 'ignore')
    if META_TAG.lower() in text.lower():
        return True
    if not fix:
        return False
    patched, n = re.subn(r'(<head[^>]*>)', r'\1\n  ' + META_TAG, text, 1, flags=re.I)
    if n:
        path.write_text(patched, 'utf-8')
        return True
    return False

def patch_robots(root: Path, fix: bool) -> bool:
    robots = root / 'robots.txt'
    content = robots.read_text('utf-8', 'ignore') if robots.exists() else ''
    compliant = all(bot.lower() in content.lower() for bot in AI_BOTS)
    if compliant or not fix:
        return compliant
    lines = [f'User-agent: {b}\nDisallow: /' for b in AI_BOTS if b.lower() not in content.lower()]
    robots.write_text((content.strip() + '\n' + '\n'.join(lines) + '\n'), 'utf-8')
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--path', default='.')
    ap.add_argument('--fix', action='store_true')
    args = ap.parse_args()
    root = Path(args.path).resolve()
    result = {}
    ok = True
    for f in find_html(root):
        res = patch_html(f, args.fix)
        result[str(f.relative_to(root))] = res
        ok &= res
    robots_ok = patch_robots(root, args.fix)
    result['robots.txt'] = robots_ok
    ok &= robots_ok
    print(json.dumps({'passed': ok, 'details': result, 'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'}, indent=2))
    if args.fix:
        import subprocess
        subprocess.run(['git', 'add', '.'])
    if not ok:
        sys.exit(1)
if __name__ == '__main__':
    main()
