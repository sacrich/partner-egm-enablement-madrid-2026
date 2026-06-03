#!/usr/bin/env python3
"""
Genera un sitio estático autocontenido con solo las 7 páginas del workshop
de Salesforce Personalization (sin navegación al resto del portal).
"""

import json
import re
import shutil
import ssl
import urllib.request
from pathlib import Path

BASE = "https://partnerworkshops.salesforce.com"
ROOT = Path(__file__).parent
COPY_JS = ROOT / "copy.js"
OUT = ROOT / "dist"
SCRAPED = ROOT / "dist-scraped"
ASSETS = OUT / "assets"
DATA_DIR = OUT / "data"

# slug -> bundle JS (desde prefetch del sitio VuePress)
PAGES = [
    {
        "slug": "setup-personalization",
        "title": "Setup Personalization",
        "bundle": "setup-personalization.html-CDB-z1KB.js",
        "meta": "Administrator · Foundational · ~1 hr",
    },
    {
        "slug": "sitemap",
        "title": "Web Sitemap",
        "bundle": "sitemap.html-CiCK46pK.js",
        "meta": "Developer · Intermediate · ~1 hr 10 mins",
    },
    {
        "slug": "web-schemas",
        "title": "Web Schemas",
        "bundle": "web-schemas.html-C-snhr66.js",
        "meta": "Developer · Intermediate · ~10 mins",
    },
    {
        "slug": "data-streams",
        "title": "Data Streams",
        "bundle": "data-streams.html-Cy_EKfQf.js",
        "meta": "Administrator · Intermediate · ~20 mins",
    },
    {
        "slug": "identity-resolution",
        "title": "Identity Resolution",
        "bundle": "identity-resolution.html-DFJm-pZx.js",
        "meta": "Developer · Foundational · ~10 mins",
    },
    {
        "slug": "item-data-graphs",
        "title": "Item Data Graphs",
        "bundle": "item-data-graphs.html-C0MuKgZb.js",
        "meta": "Administrator · Foundational · ~20 mins",
    },
    {
        "slug": "profile-data-graphs",
        "title": "Profile Data Graphs",
        "bundle": "profile-data-graphs.html-BOAoPv9O.js",
        "meta": "Administrator · Foundational · ~30 mins",
    },
]

ALLOWED_SLUGS = {p["slug"] for p in PAGES}
KEEP_ADDITIONAL_RESOURCES = {"sitemap"}
TAIL_SECTION_IDS = ("additional-resources", "related-resources")
CSS_HREF = "/assets/style-CW392w5Z.css"
VIDYARD_JS = "https://play.vidyard.com/embed/v4.js"


def fetch(url: str) -> bytes:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=120) as r:
        return r.read()


def _parse_js_quoted(js: str, start: int, quote: str) -> tuple[str, int]:
    """Lee una cadena JS entre comillas simples o dobles desde `start` (tras la comilla)."""
    buf: list[str] = []
    j = start
    while j < len(js):
        c = js[j]
        if c == "\\" and j + 1 < len(js):
            nxt = js[j + 1]
            if nxt == "n":
                buf.append("\n")
            elif nxt == "t":
                buf.append("\t")
            elif nxt in ("'", '"', "\\"):
                buf.append(nxt)
            else:
                buf.append(c)
                buf.append(nxt)
            j += 2
            continue
        if c == quote:
            return "".join(buf), j + 1
        buf.append(c)
        j += 1
    return "".join(buf), j


def extract_html_chunks(js: str) -> str:
    """Extrae fragmentos HTML embebidos en bundles Vue (helpers minificados n, o, etc.)."""
    asset_vars: dict[str, str] = {}
    for m in re.finditer(
        r'const\s+([a-zA-Z_$][\w$]*)\s*=\s*"(/assets/[^"]+)"', js
    ):
        asset_vars[m.group(1)] = m.group(2)

    def add_html(text: str, end_pos: int) -> int:
        if "<" in text and len(text) >= 40 and text not in seen:
            seen.add(text)
            chunks.append(text)
        return end_pos

    chunks: list[str] = []
    seen: set[str] = set()
    i = 0
    while i < len(js) - 3:
        # Helper minificado: n(''), o(''), i(''), t(''), etc.
        if (
            js[i].isalpha()
            and len(js[i]) == 1
            and js[i + 1 : i + 3] in ("('", '("')
        ):
            quote = js[i + 2]
            text, i = _parse_js_quoted(js, i + 3, quote)
            i = add_html(text, i)
            continue

        # e[20]||(e[20]=i('<html>',6)
        m = re.match(r"[a-z]\[\d+\]\|\|\([a-z]\[\d+\]=[a-z]\(", js[i:])
        if m and i + m.end() < len(js) and js[i + m.end()] in "'\"":
            quote = js[i + m.end()]
            text, i = _parse_js_quoted(js, i + m.end() + 1, quote)
            i = add_html(text, i)
            continue

        # Concatenación de imagen: i('<figure...'+p+'...')
        m = re.match(
            r"""[a-z]\('([^']*)'\+([a-zA-Z_$][\w$]*)\+'([^']*)'\)""", js[i:]
        )
        if m:
            pre, var, post = m.group(1), m.group(2), m.group(3)
            path = asset_vars.get(var, "")
            if path:
                combined = pre + path + post
                if combined not in seen:
                    seen.add(combined)
                    chunks.append(combined)
            i += m.end()
            continue

        i += 1

    return "\n".join(chunks)


def fix_vidyard_embeds(body: str) -> str:
    """Asegura embeds Vidyard reproducibles con v4.js."""
    body = re.sub(
        r'<vidyard\s+id="([^"]+)"\s*></vidyard>',
        r'<img class="vidyard-player-embed" src="https://play.vidyard.com/\1.jpg" '
        r'data-uuid="\1" data-v="4" data-type="inline" '
        r'style="width:100%;max-width:960px;margin:1rem auto;display:block;" />',
        body,
        flags=re.IGNORECASE,
    )
    return body


def strip_tail_resource_sections(body: str, slug: str) -> str:
    """Quita Additional Resources / Related Resources (salvo Web Sitemap)."""
    if slug in KEEP_ADDITIONAL_RESOURCES:
        return body
    cut_at: list[int] = []
    for sid in TAIL_SECTION_IDS:
        m = re.search(rf'<h2 id="{sid}"', body, re.IGNORECASE)
        if m:
            cut_at.append(m.start())
    if cut_at:
        body = body[: min(cut_at)].rstrip()
    return body


def strip_toc_resource_entries(toc_html: str, slug: str) -> str:
    if slug in KEEP_ADDITIONAL_RESOURCES:
        return toc_html
    for sid in TAIL_SECTION_IDS:
        toc_html = re.sub(
            rf'<li class="vp-toc-item"[^>]*>\s*<a[^>]*href="[^"]*#{sid}"[^>]*>.*?</a></li>\s*'
            rf'(?:<li>\s*<ul class="vp-toc-list">.*?</ul>\s*</li>\s*)?',
            "",
            toc_html,
            flags=re.DOTALL,
        )
        toc_html = re.sub(
            rf'<li>\s*<ul class="vp-toc-list">.*?#{sid}.*?</ul>\s*</li>\s*',
            "",
            toc_html,
            flags=re.DOTALL,
        )
    return toc_html


def clean_scraped_body(html: str, current_slug: str) -> str:
    """Limpia HTML scrapeado: quita migas/prev-next fuera de los 7 módulos."""
    m = re.search(r'<div id="markdown-content">(.*)</div><!----><!----><!----></div>',
                   html, re.DOTALL)
    body = m.group(1) if m else html
    body = fix_vidyard_embeds(body)
    body = strip_tail_resource_sections(body, current_slug)
    # TOC lateral del original (opcional)
    toc = re.search(r'<aside id="toc"[^>]*>.*?</aside>', html, re.DOTALL)
    toc_html = toc.group(0) if toc else ""
    if toc_html:
        toc_html = re.sub(r'href="#', f'href="{current_slug}.html#', toc_html)
        toc_html = strip_toc_resource_entries(toc_html, current_slug)
        body = f'<div class="page-with-toc"><div class="inline-toc">{toc_html}</div><div class="markdown-body">{body}</div></div>'
    else:
        body = f'<div class="markdown-body">{body}</div>'

    def fix_href(m: re.Match) -> str:
        href = m.group(1)
        if href.startswith("#"):
            return f'href="{current_slug}.html{href}"'
        if href in ALLOWED_SLUGS or href.endswith(".html") and href.replace(".html", "") in ALLOWED_SLUGS:
            return f'href="{href}"' if href.endswith(".html") else f'href="{href}.html"'
        if href.startswith("../../data/"):
            name = href.split("/")[-1]
            return f'href="data/{name}"'
        if "partnerworkshops.salesforce.com" in href:
            return 'href="#" title="Enlace al portal completo (no incluido en esta guía)"'
        return m.group(0)

    body = re.sub(r'href="([^"]+)"', fix_href, body)
    body = re.sub(
        r'href="(/workshops/salesforce-personalization/([^"]+))"',
        lambda m: (
            f'href="{m.group(2)}"'
            if m.group(2).replace(".html", "") in ALLOWED_SLUGS
            else 'href="#"'
        ),
        body,
    )
    # Enlaces relativos tipo href="sitemap"
    body = re.sub(
        r'href="(sitemap|web-schemas|data-streams|identity-resolution|item-data-graphs|profile-data-graphs|setup-personalization)"',
        r'href="\1.html"',
        body,
    )
    return body


def rewrite_html(html: str, current_slug: str) -> str:
    html = re.sub(
        r'src="/assets/',
        'src="assets/',
        html,
    )
    html = re.sub(
        r'href="/assets/',
        'href="assets/',
        html,
    )

    def replace_workshop_link(m: re.Match) -> str:
        href = m.group(1)
        if not href.startswith("/workshops/salesforce-personalization/"):
            return m.group(0)
        name = href.rstrip("/").split("/")[-1].replace(".html", "")
        if name in ALLOWED_SLUGS:
            if name == current_slug:
                return f'href="#top"'
            return f'href="{name}.html"'
        return 'href="#" onclick="return false;" title="Contenido no incluido en esta guía"'

    html = re.sub(
        r'href="(/workshops/salesforce-personalization/[^"]+)"',
        replace_workshop_link,
        html,
    )
    # Enlaces internos #anchor del mismo doc
    html = re.sub(r'href="/"', 'href="index.html"', html)
    html = re.sub(r'href="/feedback\.html"', 'href="#"', html)
    return html


def collect_asset_paths(*texts: str) -> set[str]:
    found: set[str] = set()
    for t in texts:
        for m in re.finditer(r"/assets/([a-zA-Z0-9_.-]+\.(?:png|jpg|jpeg|gif|webp|svg|woff2?|css))", t):
            found.add(m.group(1))
        for m in re.finditer(r'assets/([a-zA-Z0-9_.-]+\.(?:png|jpg|jpeg|gif|webp|svg))', t):
            found.add(m.group(1))
    return found


def download_assets(paths: set[str]) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name in sorted(paths):
        dest = ASSETS / name
        if dest.exists():
            continue
        try:
            data = fetch(f"{BASE}/assets/{name}")
            dest.write_bytes(data)
            print(f"  asset: {name}")
        except Exception as e:
            print(f"  WARN asset {name}: {e}")


def page_nav_footer(nav_items: list[dict], active: str) -> str:
    slugs = [p["slug"] for p in nav_items]
    i = slugs.index(active)
    parts = ['<nav class="vp-page-nav" aria-label="Módulos">']
    if i > 0:
        prev = nav_items[i - 1]
        parts.append(
            f'<a class="prev" href="{prev["slug"]}.html">← {prev["title"]}</a>'
        )
    if i < len(nav_items) - 1:
        nxt = nav_items[i + 1]
        parts.append(
            f'<a class="next" href="{nxt["slug"]}.html">{nxt["title"]} →</a>'
        )
    parts.append("</nav>")
    return "\n      ".join(parts)


def page_shell(title: str, meta: str, body: str, nav_items: list[dict], active: str) -> str:
    nav_lis = "\n".join(
        f'      <li><a class="nav-link{" active" if p["slug"] == active else ""}" '
        f'href="{p["slug"]}.html">{p["title"]}</a></li>'
        for p in nav_items
    )
    seq_nav = page_nav_footer(nav_items, active)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} | Salesforce Personalization Workshop</title>
  <link rel="stylesheet" href="assets/workshop.css" />
</head>
<body>
  <header class="site-header">
    <div class="site-header-inner">
      <a class="brand" href="index.html">Salesforce Personalization</a>
      <span class="badge">Theory track · 7 modules</span>
    </div>
  </header>
  <div class="layout">
    <nav class="sidebar" aria-label="Workshop modules">
      <p class="sidebar-label">Included modules</p>
      <ol class="sidebar-list">
{nav_lis}
      </ol>
      <p class="sidebar-note">Remaining Partner Workshop labs are covered in the <strong>hands-on</strong> session.</p>
    </nav>
    <main class="content" id="main-content">
      <p id="top" class="workshop-meta">{meta}</p>
      <h1 class="page-title">{title}</h1>
      <article class="vp-doc">
{body}
      </article>
      {seq_nav}
    </main>
  </div>
  <footer class="site-footer">
    <p>Partner Enablement — consolidated theory modules only.</p>
  </footer>
  <script src="assets/copy.js"></script>
  <script async src="{VIDYARD_JS}" type="text/javascript"></script>
</body>
</html>"""


def index_shell(nav_items: list[dict]) -> str:
    cards = "\n".join(
        f"""        <li class="index-card">
          <a href="{p['slug']}.html">
            <span class="index-card-num" aria-hidden="true">{i}</span>
            <h2>{p['title']}</h2>
            <p class="index-meta">{p['meta']}</p>
          </a>
        </li>"""
        for i, p in enumerate(nav_items, 1)
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Mandatory pre-work · Partner EGM Enablement 2026 · Madrid</title>
  <link rel="stylesheet" href="assets/workshop.css" />
</head>
<body class="page-home">
  <header class="site-header">
    <div class="site-header-inner site-header-inner--wide">
      <span class="brand">Salesforce Personalization</span>
      <span class="badge">Mandatory pre-work</span>
    </div>
  </header>
  <main class="home-main">
    <div class="home-hero">
      <p class="home-event-label">Partner EGM Enablement 2026 · Madrid</p>
      <h1>Mandatory pre-work before the event</h1>
      <div class="home-event-banner" role="note">
        <p class="home-event-dates"><strong>16–17 June 2026</strong> · Madrid</p>
        <p>
          Complete the seven modules below <strong>before</strong> you join us at Partner EGM Enablement 2026.
          This is the required theory and setup track so you can focus on hands-on labs during the event.
        </p>
      </div>
      <p class="lead">
        Work through all seven modules below before the event. Additional topics will be covered
        <strong>in person</strong> in Madrid.
      </p>
      <p class="lead home-modules-intro">Complete the modules in this order:</p>
    </div>
    <ol class="index-list index-list--grid">
{cards}
    </ol>
  </main>
  <footer class="site-footer site-footer--home">
    <div class="footer-home-inner">
      <p class="footer-home-title">Partner EGM Enablement 2026</p>
      <p class="footer-home-meta">16–17 June 2026 · Madrid</p>
      <p>
        Mandatory pre-work for attendees. Complete all seven modules in order before the event.
      </p>
      <p class="footer-home-note">
        Exercise links inside each module (SDO, Postman, Chrome Web Store, sample data files, etc.)
        are included only where the lab requires them.
      </p>
    </div>
  </footer>
</body>
</html>"""


def download_data_files(html: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    names: set[str] = set()
    for m in re.finditer(r"/workshops/salesforce-personalization/data/([^\"']+)", html):
        names.add(m.group(1))
    for m in re.finditer(r"\.\./\.\./data/([^\"']+)", html):
        names.add(m.group(1))
    for m in re.finditer(r"velo_[a-z_]+\.csv", html):
        names.add(m.group(0))
    for name in sorted(names):
        dest = DATA_DIR / name
        if dest.exists():
            continue
        try:
            dest.write_bytes(
                fetch(f"{BASE}/workshops/salesforce-personalization/data/{name}")
            )
            print(f"  data: {name}")
        except Exception as e:
            print(f"  WARN data {name}: {e}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_assets: set[str] = set()
    page_bodies: dict[str, str] = {}
    use_scraped = SCRAPED.exists() and any(SCRAPED.glob("*.html"))

    if not use_scraped:
        print("AVISO: No hay dist-scraped/. Ejecuta: PLAYWRIGHT_BROWSERS_PATH=./.pw-browsers node scrape-playwright.mjs")
        print("Usando extracción parcial desde bundles JS…")

    print("Preparando contenido…")
    raw_html_all = ""
    for p in PAGES:
        if use_scraped:
            scraped_path = SCRAPED / f"{p['slug']}.html"
            raw = scraped_path.read_text(encoding="utf-8")
            raw_html_all += raw
            body = clean_scraped_body(raw, p["slug"])
        else:
            url = f"{BASE}/assets/{p['bundle']}"
            js = fetch(url).decode("utf-8", errors="replace")
            body = rewrite_html(extract_html_chunks(js), p["slug"])
            body = fix_vidyard_embeds(strip_tail_resource_sections(body, p["slug"]))
            raw_html_all += body
        page_bodies[p["slug"]] = body
        all_assets |= collect_asset_paths(body)
        print(f"  OK {p['slug']} ({len(body):,} chars)")

    css_name = CSS_HREF.split("/")[-1]
    all_assets.add(css_name)

    print("\nDescargando imágenes, estilos y CSVs…")
    download_assets(all_assets)
    download_data_files(raw_html_all)

    print("\nGenerando HTML…")
    for p in PAGES:
        html = page_shell(
            p["title"],
            p["meta"],
            page_bodies[p["slug"]],
            PAGES,
            p["slug"],
        )
        (OUT / f"{p['slug']}.html").write_text(html, encoding="utf-8")
        print(f"  wrote {p['slug']}.html")

    (OUT / "index.html").write_text(index_shell(PAGES), encoding="utf-8")

    workshop_css = ASSETS / "workshop.css"
    orig_path = ASSETS / css_name
    orig = orig_path.read_text(encoding="utf-8", errors="replace") if orig_path.exists() else ""
    workshop_css.write_text(build_custom_css(orig), encoding="utf-8")

    ASSETS.mkdir(parents=True, exist_ok=True)
    shutil.copy(COPY_JS, ASSETS / "copy.js")
    print("  asset: copy.js")

    manifest = {
        "pages": [p["slug"] for p in PAGES],
        "source": BASE,
        "note": "Solo estos 7 módulos; sin sidebar del portal completo.",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUT / ".nojekyll").touch()
    print(f"\nListo → {OUT.resolve()}")


def build_custom_css(vuepress_css: str) -> str:
    # Recortar CSS enorme: usar solo reglas útiles si es muy grande
    base = ""
    if vuepress_css and len(vuepress_css) < 500_000:
        base = f"/* Estilos base VuePress */\n{vuepress_css}\n\n"

    return (
        base
        + """
:root {
  --sf-blue: #0176d3;
  --sf-navy: #032d60;
  --bg: #f4f6f9;
  --card: #fff;
  --border: #d8dde6;
  --text: #181818;
  --muted: #5c5c5c;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Salesforce Sans", system-ui, -apple-system, sans-serif;
  color: var(--text);
  background: var(--bg);
  line-height: 1.6;
}
.site-header {
  background: var(--sf-navy);
  color: #fff;
  padding: 0.75rem 1.5rem;
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0,0,0,.15);
}
.site-header-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}
.brand {
  font-weight: 700;
  font-size: 1.1rem;
  color: #fff;
  text-decoration: none;
}
.badge {
  font-size: 0.75rem;
  background: rgba(255,255,255,.15);
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
}
.layout {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 0;
  min-height: calc(100vh - 120px);
}
@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar { border-bottom: 1px solid var(--border); }
}
.sidebar {
  background: var(--card);
  border-right: 1px solid var(--border);
  padding: 1.25rem 1rem;
  position: sticky;
  top: 52px;
  align-self: start;
  max-height: calc(100vh - 52px);
  overflow-y: auto;
}
.sidebar-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  margin: 0 0 0.5rem;
}
.sidebar-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.sidebar-list .nav-link {
  display: block;
  padding: 0.45rem 0.6rem;
  border-radius: 6px;
  color: var(--text);
  text-decoration: none;
  font-size: 0.9rem;
}
.sidebar-list .nav-link:hover { background: #eef4fb; }
.sidebar-list .nav-link.active {
  background: var(--sf-blue);
  color: #fff;
  font-weight: 600;
}
.sidebar-note {
  font-size: 0.8rem;
  color: var(--muted);
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}
.content {
  background: var(--card);
  padding: 2rem 2.5rem 3rem;
}
.workshop-meta { color: var(--muted); font-size: 0.9rem; margin: 0 0 0.25rem; }
.page-title { margin-top: 0; color: var(--sf-navy); }
.vp-doc h2 { margin-top: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 0.35rem; }
.vp-doc h3 { margin-top: 1.5rem; }
.vp-doc table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.9rem; }
.vp-doc th, .vp-doc td { border: 1px solid var(--border); padding: 0.5rem 0.75rem; text-align: left; }
.vp-doc th { background: #f3f3f3; }
.vp-doc figure { margin: 1.25rem 0; }
.vp-doc img { max-width: 100%; height: auto; border: 1px solid var(--border); border-radius: 4px; }
.vp-doc figcaption { font-size: 0.85rem; color: var(--muted); margin-top: 0.35rem; }
.vp-doc code {
  background: #f3f3f3;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  font-size: 0.88em;
}
.vp-doc pre {
  background: #1e1e1e;
  color: #f8f8f2;
  padding: 1rem;
  overflow-x: auto;
  border-radius: 6px;
}
.hint-container {
  border-left: 4px solid var(--sf-blue);
  background: #eef4fb;
  padding: 0.75rem 1rem;
  margin: 1rem 0;
  border-radius: 0 6px 6px 0;
}
.hint-container.tip { border-color: #2e844a; background: #eef6f0; }
.hint-container.note { border-color: #fe9339; background: #fff8f0; }
.hint-container-title { font-weight: 700; margin: 0 0 0.35rem; }
.site-footer {
  text-align: center;
  padding: 1.5rem;
  font-size: 0.8rem;
  color: var(--muted);
  border-top: 1px solid var(--border);
  background: var(--card);
}
.site-header-inner--wide { max-width: none; padding-inline: 2.5rem; }
.page-home .site-header-inner { max-width: none; }
.home-main {
  width: 100%;
  max-width: none;
  padding: 2.5rem 3rem 4rem;
  box-sizing: border-box;
}
.home-hero { max-width: 960px; margin-bottom: 2rem; }
.home-event-label {
  margin: 0 0 0.35rem;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--sf-blue);
}
.home-hero h1 {
  margin: 0 0 1.25rem;
  font-size: clamp(1.75rem, 3vw, 2.35rem);
  color: var(--sf-navy);
  line-height: 1.2;
}
.home-event-banner {
  margin: 0 0 1.5rem;
  padding: 1.25rem 1.5rem;
  border-left: 4px solid var(--sf-blue);
  border-radius: 0 8px 8px 0;
  background: linear-gradient(90deg, #eef4fb 0%, #f8fafc 100%);
}
.home-event-banner p { margin: 0; line-height: 1.6; }
.home-event-banner p + p { margin-top: 0.75rem; }
.home-event-dates {
  font-size: 1.05rem;
  color: var(--sf-navy);
}
.home-modules-intro { margin-top: 0.5rem; }
.site-footer--home {
  text-align: left;
  padding: 2rem 3rem 2.5rem;
  background: var(--sf-navy);
  color: rgba(255, 255, 255, 0.92);
  border-top: none;
}
.footer-home-inner { max-width: 960px; }
.footer-home-title {
  margin: 0 0 0.25rem;
  font-size: 1.1rem;
  font-weight: 700;
  color: #fff;
}
.footer-home-meta {
  margin: 0 0 1rem;
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.75);
}
.site-footer--home p {
  margin: 0 0 0.75rem;
  font-size: 0.9rem;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.88);
}
.footer-home-note {
  margin-top: 1rem !important;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  font-size: 0.82rem !important;
  color: rgba(255, 255, 255, 0.65) !important;
}
.index-list--grid {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.25rem;
  width: 100%;
}
.index-card {
  margin: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card);
  height: 100%;
}
.index-card a {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 1.25rem 1.5rem;
  text-decoration: none;
  color: inherit;
}
.index-card a:hover {
  border-color: var(--sf-blue);
  box-shadow: 0 4px 16px rgba(1, 118, 211, 0.15);
}
.index-card-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  margin-bottom: 0.65rem;
  border-radius: 50%;
  background: var(--sf-blue);
  color: #fff;
  font-weight: 700;
  font-size: 1rem;
  line-height: 1;
}
.index-card h2 { margin: 0 0 0.35rem; font-size: 1.2rem; color: var(--sf-blue); }
.index-meta { margin: 0; color: var(--muted); font-size: 0.9rem; }
.lead { font-size: 1.1rem; line-height: 1.65; max-width: 72ch; }
.vidyard-player-embed { min-height: 360px; cursor: pointer; }
.copy-button,
.vp-copy-code-button {
  cursor: pointer;
  pointer-events: auto;
}
.copy-button.is-copied,
.vp-copy-code-button.is-copied {
  outline: 2px solid var(--sf-blue);
  outline-offset: 2px;
}
.vp-doc div[style*="position: relative"] .copy-button {
  vertical-align: middle;
}
.page-with-toc { display: grid; grid-template-columns: 220px 1fr; gap: 2rem; }
@media (max-width: 900px) { .page-with-toc { grid-template-columns: 1fr; } }
.inline-toc { font-size: 0.85rem; position: sticky; top: 4rem; align-self: start; max-height: 80vh; overflow-y: auto; }
.inline-toc .vp-toc-list { list-style: none; padding-left: 0; }
.inline-toc a { color: var(--sf-blue); text-decoration: none; }
.inline-toc a:hover { text-decoration: underline; }
.markdown-body { min-width: 0; }
.vp-page-nav { display: flex; gap: 1rem; margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid var(--border); }
.vp-page-nav a { color: var(--sf-blue); text-decoration: none; font-weight: 600; }
.hint-container.important { border-color: #c23934; background: #fef5f5; }
vidyard { display: block; margin: 1rem 0; min-height: 360px; background: #f3f3f3; border-radius: 6px; }
"""
    )


if __name__ == "__main__":
    main()
