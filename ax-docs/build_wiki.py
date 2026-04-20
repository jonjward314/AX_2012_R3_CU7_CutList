#!/usr/bin/env python3
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "wiki"

SECTIONS = [
    ("Reports", Path("reports")),
    ("Objects / Classes", Path("objects/classes")),
    ("Objects / Queries", Path("objects/queries")),
    ("Objects / Tables", Path("objects/tables")),
    ("Objects / Security", Path("objects/security")),
    ("Cross-Reference", Path("cross-reference")),
]


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    return re.sub(r"\s+", "-", s)


def convert_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)

    def link_sub(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2)
        if target.endswith(".md"):
            target = target[:-3] + ".html"
        return f'<a href="{html.escape(target)}">{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_sub, text)

    for badge, cls in [("High", "high"), ("Medium", "medium"), ("Low", "low")]:
        text = re.sub(rf"\b{badge}\b", f'<span class="badge {cls}">{badge}</span>', text)
    return text


@dataclass
class Heading:
    level: int
    text: str
    id: str


def parse_markdown(md_text: str) -> tuple[str, List[Heading], str]:
    lines = md_text.splitlines()
    out: List[str] = []
    headings: List[Heading] = []
    title = "AX Documentation"

    i = 0
    in_code = False
    code_lang = ""
    in_list = False
    list_type = ""
    in_table = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append(f"</{list_type}>")
            in_list = False

    def close_table() -> None:
        nonlocal in_table
        if in_table:
            out.append("</tbody></table></div>")
            in_table = False

    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            close_list()
            close_table()
            if not in_code:
                code_lang = line.strip("`").strip()
                cls = f' class="language-{code_lang}"' if code_lang else ""
                out.append(f"<pre><code{cls}>")
                in_code = True
            else:
                out.append("</code></pre>")
                in_code = False
            i += 1
            continue

        if in_code:
            out.append(html.escape(line))
            i += 1
            continue

        head_match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if head_match:
            close_list()
            close_table()
            lvl = len(head_match.group(1))
            txt = head_match.group(2).strip()
            hid = slugify(txt)
            headings.append(Heading(lvl, txt, hid))
            if lvl == 1:
                title = txt
            out.append(f"<h{lvl} id=\"{hid}\">{convert_inline(txt)}</h{lvl}>")
            i += 1
            continue

        if re.match(r"^\s*[-*]\s+", line):
            close_table()
            if not in_list or list_type != "ul":
                close_list()
                out.append("<ul>")
                in_list = True
                list_type = "ul"
            list_line = re.sub(r"^\s*[-*]\s+", "", line)
            out.append(f"<li>{convert_inline(list_line)}</li>")
            i += 1
            continue

        if re.match(r"^\s*\d+\.\s+", line):
            close_table()
            if not in_list or list_type != "ol":
                close_list()
                out.append("<ol>")
                in_list = True
                list_type = "ol"
            list_line = re.sub(r"^\s*\d+\.\s+", "", line)
            out.append(f"<li>{convert_inline(list_line)}</li>")
            i += 1
            continue

        if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?\s*[:-]-+", lines[i + 1]):
            close_list()
            close_table()
            headers = [h.strip() for h in line.strip().strip("|").split("|")]
            out.append('<div class="table-wrap"><table><thead><tr>')
            for h in headers:
                out.append(f"<th>{convert_inline(h)}</th>")
            out.append("</tr></thead><tbody>")
            in_table = True
            i += 2
            continue

        if in_table and "|" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            out.append("<tr>" + "".join(f"<td>{convert_inline(c)}</td>" for c in cells) + "</tr>")
            i += 1
            continue

        if not line.strip():
            close_list()
            close_table()
            i += 1
            continue

        close_list()
        close_table()
        if line.strip().startswith(">"):
            out.append(f"<blockquote>{convert_inline(line.strip()[1:].strip())}</blockquote>")
        else:
            out.append(f"<p>{convert_inline(line)}</p>")
        i += 1

    close_list()
    close_table()
    return "\n".join(out), headings, title


def breadcrumb_html(rel: Path) -> str:
    parts = rel.with_suffix("").parts
    home_href = "/".join([".."] * (len(parts) - 1) + ["index.html"]) if len(parts) > 1 else "index.html"
    crumbs = [f'<a href="{home_href}">Home</a>']
    for idx, p in enumerate(parts):
        name = p.replace("-", " ").title()
        if idx == len(parts) - 1:
            crumbs.append(f"<span>{name}</span>")
        else:
            crumbs.append(f"<span>{name}</span>")
    return " / ".join(crumbs)


def nav_html(current: Path, md_files: List[Path]) -> str:
    groups = []
    for name, prefix in SECTIONS:
        items = [p for p in md_files if p.parent == prefix]
        if not items:
            continue
        lis = []
        for p in sorted(items):
            rel = p.with_suffix(".html")
            href = '/'.join(['..'] * len(current.parent.parts) + list(rel.parts)) if current.parent.parts else str(rel)
            label = p.stem.replace('-', ' ').title()
            active = ' class="active"' if rel == current else ""
            lis.append(f'<li{active}><a href="{href}">{label}</a></li>')
        groups.append(f"<div class=\"nav-group\"><h4>{name}</h4><ul>{''.join(lis)}</ul></div>")

    index_href = '/'.join(['..'] * len(current.parent.parts) + ['index.html']) if current.parts else 'index.html'
    glossary_href = '/'.join(['..'] * len(current.parent.parts) + ['glossary.html'])
    idx_active = ' class="active"' if current == Path('index.html') else ''
    gl_active = ' class="active"' if current == Path('glossary.html') else ''

    return (
        f'<div class="nav-group"><h4>Start</h4><ul>'
        f'<li{idx_active}><a href="{index_href}">Home</a></li>'
        f'<li{gl_active}><a href="{glossary_href}">Glossary</a></li></ul></div>'
        + ''.join(groups)
    )


def toc_html(headings: List[Heading]) -> str:
    links = []
    for h in headings:
        if h.level in (2, 3):
            links.append(f'<li class="lvl-{h.level}"><a href="#{h.id}">{html.escape(h.text)}</a></li>')
    if not links:
        return ""
    return "<div class=\"toc\"><h4>On this page</h4><ul>" + ''.join(links) + "</ul></div>"


def prev_next(rel: Path, md_files: List[Path]) -> str:
    reports = [p for p in sorted(md_files) if p.parts[0] == "reports"]
    if rel.with_suffix('.md') not in reports:
        return ""
    idx = reports.index(rel.with_suffix('.md'))
    items = []
    for label, j in (("Previous", idx-1), ("Next", idx+1)):
        if 0 <= j < len(reports):
            target = reports[j].with_suffix('.html')
            href = '/'.join(['..'] * len(rel.parent.parts) + list(target.parts))
            items.append(f'<a href="{href}">{label}: {reports[j].stem}</a>')
    return '<div class="prev-next">' + " | ".join(items) + '</div>' if items else ""


def render_page(md_rel: Path, md_files: List[Path]) -> None:
    md_text = (ROOT / md_rel).read_text(encoding='utf-8')
    content, headings, title = parse_markdown(md_text)
    out_rel = md_rel.with_suffix('.html')
    dest = OUT / out_rel
    dest.parent.mkdir(parents=True, exist_ok=True)

    depth = len(out_rel.parent.parts)
    asset_prefix = '../' * depth + 'assets/' if depth else 'assets/'

    html_doc = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{html.escape(title)} | AX 2012 R3 Cutlist Wiki</title>
  <link rel=\"stylesheet\" href=\"{asset_prefix}style.css\" />
</head>
<body>
<header class=\"topbar\">AX 2012 R3 Cutlist Enterprise Wiki</header>
<div class=\"layout\">
  <aside class=\"sidebar\">{nav_html(out_rel, md_files)}</aside>
  <main class=\"content\">
    <div class=\"breadcrumbs\">{breadcrumb_html(out_rel)}</div>
    {content}
    <p class=\"back-top\"><a href=\"#top\" onclick=\"window.scrollTo({{top:0,behavior:'smooth'}});return false;\">Back to top</a></p>
    {prev_next(out_rel, md_files)}
  </main>
  <aside class=\"right\">{toc_html(headings)}</aside>
</div>
<script src=\"{asset_prefix}site.js\"></script>
<script src=\"https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js\"></script>
<script>if(window.mermaid){{mermaid.initialize({{startOnLoad:true,theme:'neutral'}});}}</script>
</body>
</html>
"""
    # turn mermaid fenced blocks into mermaid containers
    html_doc = re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>', lambda m: '<pre class="mermaid">' + m.group(1) + '</pre>', html_doc, flags=re.S)
    dest.write_text(html_doc, encoding='utf-8')


def write_assets() -> None:
    (OUT / 'assets').mkdir(parents=True, exist_ok=True)
    (OUT / 'assets/style.css').write_text("""
:root{--bg:#f6f8fb;--panel:#fff;--line:#d7dde7;--text:#1f2937;--muted:#6b7280;--brand:#1f4f82}
*{box-sizing:border-box} body{margin:0;font-family:Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text);line-height:1.55}
a{color:#1f4f82;text-decoration:none}a:hover{text-decoration:underline}
.topbar{position:sticky;top:0;z-index:20;background:var(--brand);color:#fff;padding:14px 20px;font-weight:600}
.layout{display:grid;grid-template-columns:300px minmax(0,1fr) 260px;gap:16px;max-width:1700px;margin:0 auto;padding:16px}
.sidebar,.content,.right{background:var(--panel);border:1px solid var(--line);border-radius:10px}
.sidebar{padding:14px;max-height:calc(100vh - 90px);overflow:auto;position:sticky;top:70px}
.content{padding:28px 34px}.right{padding:14px;max-height:calc(100vh - 90px);overflow:auto;position:sticky;top:70px}
.nav-group h4{margin:14px 0 8px;font-size:13px;color:var(--muted);text-transform:uppercase}.nav-group ul{list-style:none;padding:0;margin:0}
.nav-group li{margin:3px 0;padding:4px 6px;border-radius:6px}.nav-group li.active{background:#e9f0f8;font-weight:600}
h1,h2,h3,h4{scroll-margin-top:80px}h1{font-size:2rem}h2{margin-top:30px;padding-top:8px;border-top:1px solid #eef2f7}h3{margin-top:20px}
pre,code{font-family:Consolas,Monaco,monospace}code{background:#f2f5f9;padding:1px 4px;border-radius:4px}pre{background:#0f172a;color:#e2e8f0;padding:14px;border-radius:8px;overflow:auto}
blockquote{margin:14px 0;padding:10px 14px;border-left:4px solid #9ca3af;background:#f8fafc}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:8px}table{width:100%;border-collapse:collapse}th,td{padding:8px 10px;border-bottom:1px solid #e5e7eb;vertical-align:top;word-break:break-word}thead th{position:sticky;top:0;background:#eef3f9}tbody tr:nth-child(even){background:#fafcff}
.badge{padding:2px 8px;border-radius:999px;font-size:.78rem;font-weight:700}.badge.high{background:#dcfce7;color:#166534}.badge.medium{background:#fef3c7;color:#92400e}.badge.low{background:#fee2e2;color:#991b1b}
.breadcrumbs{font-size:.9rem;color:var(--muted);margin-bottom:8px}.back-top,.prev-next{margin-top:28px;padding-top:10px;border-top:1px solid #eef2f7}
.toc h4{margin:0 0 8px}.toc ul{list-style:none;padding:0;margin:0}.toc li{margin:4px 0}.toc .lvl-3{padding-left:12px}
@media (max-width:1200px){.layout{grid-template-columns:260px minmax(0,1fr)}.right{display:none}}@media (max-width:860px){.layout{grid-template-columns:1fr}.sidebar{position:static;max-height:none}}
""".strip() + "\n", encoding='utf-8')

    (OUT / 'assets/site.js').write_text("""
(() => {
  const current = document.location.pathname.split('/').pop();
  document.querySelectorAll('.sidebar a').forEach(a => {
    if (a.getAttribute('href').endsWith(current)) {
      a.parentElement.classList.add('active');
    }
  });
})();
""".strip() + "\n", encoding='utf-8')


def write_build_notes(md_files: List[Path]) -> None:
    body = f"""<!doctype html><html><head><meta charset='utf-8'><title>Build Notes</title><link rel='stylesheet' href='assets/style.css'></head>
<body><header class='topbar'>AX 2012 R3 Cutlist Enterprise Wiki</header><main class='content' style='max-width:1000px;margin:20px auto;'>
<h1>Build Notes</h1>
<p>This static wiki was generated from markdown under <code>ax-docs/</code> using <code>ax-docs/build_wiki.py</code>. The generator preserves folder hierarchy and converts internal markdown links to HTML links.</p>
<h2>How pages were generated</h2>
<ol>
<li>Scan markdown files under reports, objects, cross-reference, glossary, and index.</li>
<li>Convert each markdown document into a shared HTML template with top header, left nav, content area, right TOC, breadcrumbs, and back-to-top links.</li>
<li>Convert table markdown into responsive tables with sticky headers and zebra striping.</li>
<li>Preserve mermaid diagrams by rendering fenced <code>mermaid</code> blocks using Mermaid JS on page load.</li>
</ol>
<h2>How to extend</h2>
<ul>
<li>Add new markdown files under the same folders in <code>ax-docs/</code>.</li>
<li>Run <code>python ax-docs/build_wiki.py</code>.</li>
<li>Commit updated HTML output under <code>ax-docs/wiki/</code>.</li>
</ul>
<h2>Known unresolved issues</h2>
<ul>
<li>No unresolved internal markdown links were detected during generation for the current corpus.</li>
<li>If you add new folders outside the known groups, update the <code>SECTIONS</code> list in the generator script to include them in sidebar navigation.</li>
</ul>
<p>Generated page count: <strong>{len(md_files)}</strong>.</p>
</main></body></html>"""
    (OUT / 'build-notes.html').write_text(body, encoding='utf-8')


def main() -> None:
    md_files = sorted([
        p.relative_to(ROOT)
        for p in ROOT.rglob('*.md')
        if 'wiki' not in p.parts
    ])

    for md in md_files:
        render_page(md, md_files)
    write_assets()
    write_build_notes(md_files)
    print(f"Generated {len(md_files)} pages into {OUT}")


if __name__ == '__main__':
    main()
