#!/usr/bin/env python3
"""Regenerate the dynamic parts of the GitHub profile README.

Writes:
  assets/header-{dark,light}.svg  animated banner
  assets/stats-{dark,light}.svg   repo stats + language breakdown
  assets/stack-{dark,light}.svg   languages / tools strip (icons vendored in
                                  assets/icons from simple-icons, CC0)
  README.md                       section between RECENT:START / RECENT:END

Stdlib only. Set GITHUB_TOKEN to avoid the 60 req/hr anonymous limit.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USER = os.environ.get("PROFILE_USER", "anubabajide")
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
README = ROOT / "README.md"

NAME = "Aanu Babajide"
WORDS = ["learner.", "eater.", "engineer."]

# Notebook outputs and generated markup inflate byte counts without saying
# much about what was actually written.
IGNORED_LANGS = {"Jupyter Notebook"}
RECENT_COUNT = 5
EXCLUDED_REPOS = {USER}

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "fg": "#e6edf3",
        "muted": "#8b949e",
        "grid": "#21262d",
        "a1": "#2dd4bf",
        "a2": "#a78bfa",
        "track": "#21262d",
    },
    "light": {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "fg": "#1f2328",
        "muted": "#59636e",
        "grid": "#eaeef2",
        "a1": "#0f766e",
        "a2": "#7c3aed",
        "track": "#eaeef2",
    },
}

# (label, simple-icons slug, colour on dark, colour on light). Icons live in
# assets/icons so the README has no external image dependencies: GitHub's
# camo proxy times out on third-party badge hosts intermittently.
STACK = {
    "LANGUAGES": [
        ("Python", "python", "#4B8BBE", "#3572A5"),
        ("TypeScript", "typescript", "#3178C6", "#3178C6"),
        ("JavaScript", "javascript", "#F7DF1E", "#C9A800"),
        ("Java", "openjdk", "#E76F00", "#B07219"),
        ("C++", "cplusplus", "#659AD2", "#00599C"),
        ("Bash", "gnubash", "#89E051", "#4EAA25"),
    ],
    "TOOLS": [
        ("React", "react", "#61DAFB", "#087EA4"),
        ("Node.js", "nodedotjs", "#5FA04E", "#5FA04E"),
        ("Django", "django", "#44B78B", "#092E20"),
        ("Flask", "flask", "#E6EDF3", "#1F2328"),
        ("Docker", "docker", "#2496ED", "#2496ED"),
        ("AWS", "amazonwebservices", "#FF9900", "#232F3E"),
        ("GCP", "googlecloud", "#4285F4", "#4285F4"),
        ("Linux", "linux", "#FCC624", "#1F2328"),
    ],
}

# Subset of GitHub linguist colours.
LANG_COLORS = {
    "Python": "#3572A5",
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Java": "#b07219",
    "C++": "#f34b7d",
    "HTML": "#e34c26",
    "CSS": "#663399",
    "SCSS": "#c6538c",
    "Shell": "#89e051",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Kotlin": "#A97BFF",
    "Dockerfile": "#384d54",
}
FALLBACK_COLOR = "#8b949e"

SANS = "ui-sans-serif,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"


# --------------------------------------------------------------------------- api

def api(path: str):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", f"{USER}-profile-updater")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_repos() -> list[dict]:
    repos, page = [], 1
    while True:
        batch = api(f"/users/{USER}/repos?type=owner&per_page=100&page={page}")
        repos.extend(batch)
        if len(batch) < 100:
            return repos
        page += 1


# ------------------------------------------------------------------------ header

def header_svg(t: dict) -> str:
    words = "".join(
        f'<text class="mono word w{i}" x="64" y="250"><tspan class="arrow">→</tspan> {escape(w)}<tspan class="cursor">_</tspan></text>'
        for i, w in enumerate(WORDS)
    )
    # Small constellation on the right; nodes pulse out of phase.
    nodes = [(930, 90), (1010, 150), (1090, 80), (1120, 200), (980, 240), (1060, 260)]
    edges = [(0, 1), (1, 2), (1, 3), (1, 4), (4, 5), (3, 5), (2, 3)]
    lines = "".join(
        f'<line x1="{nodes[a][0]}" y1="{nodes[a][1]}" x2="{nodes[b][0]}" y2="{nodes[b][1]}"/>'
        for a, b in edges
    )
    circles = "".join(
        f'<circle class="node n{i % 3}" cx="{x}" cy="{y}" r="{7 if i == 1 else 5}"/>'
        for i, (x, y) in enumerate(nodes)
    )
    n = len(WORDS)
    period = 3 * n
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="320" viewBox="0 0 1200 320" role="img" aria-label="{NAME}: learner, eater, engineer">
<style>
  .name {{ font: 800 64px {SANS}; fill: {t['fg']}; letter-spacing: -1.5px; }}
  .mono {{ font: 500 26px {MONO}; fill: {t['muted']}; }}
  .prompt {{ fill: {t['a1']}; }}
  .arrow {{ fill: {t['a2']}; }}
  .word {{ fill: {t['fg']}; opacity: 0; animation: cycle {period}s ease-in-out infinite; }}
  {''.join(f'.w{i} {{ animation-delay: {3 * i}s; }} ' for i in range(n))}
  @keyframes cycle {{
    0% {{ opacity: 0; }}
    {round(100 / n * 0.12, 2)}% {{ opacity: 1; }}
    {round(100 / n * 0.88, 2)}% {{ opacity: 1; }}
    {round(100 / n, 2)}%, 100% {{ opacity: 0; }}
  }}
  .cursor {{ fill: {t['a1']}; animation: blink 1.1s steps(1) infinite; }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  .edges line {{ stroke: {t['border']}; stroke-width: 1.5; }}
  .node {{ fill: {t['a1']}; animation: pulse 3.6s ease-in-out infinite; }}
  .n1 {{ fill: {t['a2']}; animation-delay: 1.2s; }}
  .n2 {{ animation-delay: 2.4s; }}
  @keyframes pulse {{ 0%, 100% {{ opacity: .35; }} 50% {{ opacity: 1; }} }}
  @media (prefers-reduced-motion: reduce) {{
    * {{ animation: none !important; }}
    .w{n - 1} {{ opacity: 1; }}
  }}
</style>
<defs>
  <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
    <circle cx="2" cy="2" r="1.2" fill="{t['grid']}"/>
  </pattern>
  <linearGradient id="bar" x1="0" x2="1">
    <stop offset="0" stop-color="{t['a1']}"/><stop offset="1" stop-color="{t['a2']}"/>
  </linearGradient>
  <linearGradient id="fade" x1="0" x2="1">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".55" stop-color="#fff" stop-opacity="1"/>
  </linearGradient>
  <mask id="m"><rect width="1200" height="320" fill="url(#fade)"/></mask>
  <clipPath id="card"><rect x="1" y="1" width="1198" height="318" rx="16"/></clipPath>
</defs>
<g clip-path="url(#card)">
  <rect width="1200" height="320" fill="{t['bg']}"/>
  <rect width="1200" height="320" fill="url(#grid)" mask="url(#m)"/>
  <rect width="1200" height="5" fill="url(#bar)"/>
</g>
<rect x="1" y="1" width="1198" height="318" rx="16" fill="none" stroke="{t['border']}" stroke-width="1.5"/>
<text class="name" x="64" y="140">{NAME}</text>
<text class="mono" x="64" y="204"><tspan class="prompt">$</tspan> whoami</text>
{words}
<g class="edges">{lines}</g>
{circles}
</svg>
"""


# ------------------------------------------------------------------------- stats

def stats_svg(t: dict, s: dict) -> str:
    w, h = 1200, 220
    # Left column: headline numbers.
    tiles = [
        (str(s["repos"]), "public repos"),
        (str(s["stars"]), "stars earned"),
        (str(s["years"]), "years on GitHub"),
    ]
    tile_svg = "".join(
        f'<text class="big" x="{64 + i * 150}" y="112">{escape(v)}</text>'
        f'<text class="label" x="{64 + i * 150}" y="140">{escape(k)}</text>'
        for i, (v, k) in enumerate(tiles)
    )

    # Right column: stacked language bar + legend.
    bx, bw, by = 560, 576, 84
    segs, x = [], float(bx)
    for lang, pct in s["langs"]:
        seg_w = bw * pct
        segs.append(
            f'<rect x="{x:.1f}" y="{by}" width="{max(seg_w - 2, 1):.1f}" height="12" '
            f'fill="{LANG_COLORS.get(lang, FALLBACK_COLOR)}"/>'
        )
        x += seg_w
    legend = []
    for i, (lang, pct) in enumerate(s["langs"]):
        col, row = i % 3, i // 3
        lx, ly = bx + col * 196, by + 50 + row * 32
        legend.append(
            f'<circle cx="{lx + 6}" cy="{ly - 6}" r="6" fill="{LANG_COLORS.get(lang, FALLBACK_COLOR)}"/>'
            f'<text class="lang" x="{lx + 20}" y="{ly}">{escape(lang)} '
            f'<tspan class="pct">{pct * 100:.1f}%</tspan></text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="GitHub stats for {USER}">
<style>
  .big {{ font: 800 44px {SANS}; fill: {t['fg']}; }}
  .label {{ font: 500 15px {SANS}; fill: {t['muted']}; }}
  .head {{ font: 600 13px {MONO}; fill: {t['a1']}; letter-spacing: 1.5px; }}
  .lang {{ font: 600 16px {SANS}; fill: {t['fg']}; }}
  .pct {{ font-weight: 400; fill: {t['muted']}; }}
  .foot {{ font: 400 12px {MONO}; fill: {t['muted']}; }}
  .grow {{ transform-origin: {bx}px 0; animation: grow 1.2s cubic-bezier(.2,.8,.2,1) both; }}
  @keyframes grow {{ from {{ transform: scaleX(0); }} }}
  @media (prefers-reduced-motion: reduce) {{ .grow {{ animation: none; }} }}
</style>
<defs><clipPath id="barclip"><rect x="{bx}" y="{by}" width="{bw}" height="12" rx="6"/></clipPath></defs>
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="16" fill="{t['bg']}" stroke="{t['border']}" stroke-width="1.5"/>
<text class="head" x="64" y="56">BY THE NUMBERS</text>
<text class="head" x="{bx}" y="56">LANGUAGES I WRITE</text>
{tile_svg}
<rect x="{bx}" y="{by}" width="{bw}" height="12" rx="6" fill="{t['track']}"/>
<g clip-path="url(#barclip)"><g class="grow">{''.join(segs)}</g></g>
{''.join(legend)}
<text class="foot" x="64" y="{h - 28}">last push {escape(s['last_push'])} · auto-updated daily</text>
</svg>
"""


# ------------------------------------------------------------------------- stack

def icon_path(slug: str) -> str:
    svg = (ASSETS / "icons" / f"{slug}.svg").read_text()
    m = re.search(r'<path[^>]*\sd="([^"]+)"', svg)
    if not m:
        raise SystemExit(f"no path in icon {slug}")
    return m.group(1)


def stack_svg(t: dict, dark: bool) -> str:
    w, pad = 1200, 64
    char_w, pill_h, gap = 9.8, 40, 12  # mono 16px ~ 0.6em per glyph
    body, y = [], 56
    for label, items in STACK.items():
        body.append(f'<text class="head" x="{pad}" y="{y}">{label}</text>')
        x, py = pad, y + 18
        for name, slug, c_dark, c_light in items:
            pw = round(16 + 20 + 10 + len(name) * char_w + 18)
            body.append(
                f'<g class="pill">'
                f'<rect x="{x}" y="{py}" width="{pw}" height="{pill_h}" rx="{pill_h // 2}"/>'
                f'<svg x="{x + 16}" y="{py + 10}" width="20" height="20" viewBox="0 0 24 24">'
                f'<path fill="{c_dark if dark else c_light}" d="{icon_path(slug)}"/></svg>'
                f'<text class="name" x="{x + 46}" y="{py + 26}">{escape(name)}</text></g>'
            )
            x += pw + gap
        y += 100
    h = y - 24
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Languages and tools">
<style>
  .head {{ font: 600 13px {MONO}; fill: {t['a1']}; letter-spacing: 1.5px; }}
  .name {{ font: 500 16px {MONO}; fill: {t['fg']}; }}
  .pill rect {{ fill: {t['track']}; stroke: {t['border']}; }}
</style>
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="16" fill="{t['bg']}" stroke="{t['border']}" stroke-width="1.5"/>
{''.join(body)}
</svg>
"""


# ------------------------------------------------------------------------ readme

def recent_md(repos: list[dict]) -> str:
    rows = []
    for r in repos:
        desc = (r.get("description") or "").strip().rstrip(".")
        meta = " · ".join(
            x for x in [r.get("language"), datetime.fromisoformat(
                r["pushed_at"].replace("Z", "+00:00")).strftime("%b %Y")] if x
        )
        line = f"- [**{r['name']}**]({r['html_url']})"
        if desc:
            line += f" — {desc}"
        rows.append(f"{line} <sub>{meta}</sub>")
    return "\n".join(rows)


def replace_block(text: str, tag: str, body: str) -> str:
    pattern = re.compile(rf"(<!-- {tag}:START -->)(.*?)(<!-- {tag}:END -->)", re.S)
    if not pattern.search(text):
        raise SystemExit(f"README is missing <!-- {tag}:START/END --> markers")
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text)


# -------------------------------------------------------------------------- main

def main() -> None:
    user = api(f"/users/{USER}")
    repos = [r for r in fetch_repos() if not r["fork"] and not r["archived"]]

    lang_bytes: dict[str, int] = {}
    for r in repos:
        for lang, n in api(f"/repos/{USER}/{r['name']}/languages").items():
            if lang not in IGNORED_LANGS:
                lang_bytes[lang] = lang_bytes.get(lang, 0) + n
    total = sum(lang_bytes.values()) or 1
    top = sorted(lang_bytes.items(), key=lambda kv: kv[1], reverse=True)[:6]
    langs = [(k, v / total) for k, v in top]

    created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    recent = sorted(
        (r for r in repos if r["name"] not in EXCLUDED_REPOS),
        key=lambda r: r["pushed_at"],
        reverse=True,
    )
    stats = {
        "repos": user["public_repos"],
        "stars": sum(r["stargazers_count"] for r in repos),
        "years": (now - created).days // 365,
        "langs": langs,
        "last_push": datetime.fromisoformat(
            recent[0]["pushed_at"].replace("Z", "+00:00")).strftime("%d %b %Y") if recent else "—",
    }

    ASSETS.mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        (ASSETS / f"header-{name}.svg").write_text(header_svg(theme))
        (ASSETS / f"stats-{name}.svg").write_text(stats_svg(theme, stats))
        (ASSETS / f"stack-{name}.svg").write_text(stack_svg(theme, name == "dark"))

    README.write_text(replace_block(README.read_text(), "RECENT", recent_md(recent[:RECENT_COUNT])))


if __name__ == "__main__":
    main()
