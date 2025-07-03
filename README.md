# NoAI Guardian GitHub Action 🛡️  

**Author:** Rahul Rao Natarajan · rahulraonatarajan@gmail.com  
Automate AI‑opt‑out compliance for any website or static‑site codebase.

A single GitHub Action that **audits** your repository for AI‑opt‑out protections and can **auto‑remediate** violations in the same run.

| What it does | How |
|--------------|-----|
| **Audit** every HTML file for `<meta name="robots" content="noai, noimageai">` | Regex/DOM scan, JSON report |
| **Audit** `robots.txt` for AI‑crawler blocks (GPTBot, Google‑Extended, ClaudeBot, Perplexity…) | Pattern matching |
| **Auto‑Fix** *(optional)* | Injects missing meta tag after `<head>` and appends missing bot rules to `robots.txt` |
| **CI fail gate** | Exits non‑zero if violations remain |
| **Git staging** | When `fix: true`, runs `git add .` so later steps can commit/PR them |

---

## Quick Start

Create `.github/workflows/noai.yml` in your repo:

```yaml
name: AI Opt-Out CI
on: [push]

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # -------- Audit-only (red build if violations remain) --------
      - uses: rahulrao/noai-guardian-action@v0.1.0
        with:
          path: '.'

      # -------- Audit + auto-fix + open PR -------------------------
      - uses: rahulrao/noai-guardian-action@v0.1.0
        id: guard
        with:
          path: '.'
          fix: 'true'       # patch files & git add them

      # Commit & PR the staged fixes
      - uses: peter-evans/create-pull-request@v5
        if: failure()       # runs only when Guardian found problems
        with:
          branch: noai/fixes
          title: 'chore: AI opt-out compliance fixes'
```

---

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `path` | `.` | Directory to scan (usually repo root) |
| `fix`  | `false` | `true` ⇒ auto‑patch violations and `git add` the changes |

---

## What Gets Checked

| Layer          | Pass condition |
|----------------|----------------|
| **HTML meta**  | `<meta name="robots" content="noai, noimageai">` present anywhere inside `<head>` |
| **robots.txt** | Includes `Disallow: /` rules for GPTBot, Google‑Extended, Anthropic/Claude, PerplexityBot, CCBot, aiCrawler |

### Auto‑Fix Details (`fix: true`)

1. **Meta tag** is inserted right after the first `<head>` (idempotent).  
2. **robots.txt** is created (if missing) or appended with any missing bot rules.  
3. Files are **staged** so a later step (e.g., `create-pull-request`) can commit them.

---

## Local Test

```bash
# Build the container image
docker build -t noai-guardian .

# Audit mode (non-fix)
docker run --rm -v "$PWD":/repo -w /repo noai-guardian --path .

# Audit + auto-fix
docker run --rm -v "$PWD":/repo -w /repo noai-guardian --path . --fix
```

---

## Roadmap ▶️

| Version | Planned feature |
|---------|-----------------|
| **v0.2** | _Tiny SLM mode_ – optional flag to invoke TinyLlama‑1.1B for context‑aware, line‑preserving diffs |
| **v0.3** | Scheduled monitoring: nightly crawl + Slack / email alerts |
| **v0.4** | Edge injector: Cloudflare Worker to add headers/tags on the fly for locked‑down CMSs |

---

## Contributing

PRs + issues welcome!  
* Style: run `black .` before committing.  
* Tests: add unit tests for new logic under `tests/`.

---

## License

MIT © 2025 Rahul Rao Natarajan
