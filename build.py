#!/usr/bin/env python3
"""Generador estático de nexoapr.cl (sin dependencias externas).

Uso:  python3 build.py            -> genera dist/
Contenido:
  content/pages/*.html   páginas fijas (campo path)
  content/posts/*.html   artículos; URL /AAAA/MM/slug.html
Cada archivo empieza con un bloque de metadatos entre <!-- y -->.
"""
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
from email.utils import format_datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = json.load(open(os.path.join(ROOT, "site.json"), encoding="utf-8"))
BASE = SITE["base_url"].rstrip("/")
DIST = os.path.join(ROOT, "dist")
NOW = dt.datetime.now(dt.timezone.utc)
YEAR = str(NOW.year)
BUILD = NOW.strftime("%Y%m%d%H%M")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(rel, text):
    out = os.path.join(DIST, rel.lstrip("/"))
    if out.endswith("/"):
        out += "index.html"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)


def parse(path):
    raw = read(path)
    m = re.match(r"\s*<!--(.*?)-->\s*", raw, re.S)
    if not m:
        sys.exit(f"ERROR: {path} no tiene bloque de metadatos")
    meta = {}
    for line in m.group(1).strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    meta["body"] = raw[m.end():].strip()
    meta["source"] = os.path.relpath(path, ROOT)
    return meta


def esc(s):
    return html.escape(s or "", quote=True)


def strip_tags(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def faq_items(body):
    items = []
    for q, a in re.findall(r"<details[^>]*>\s*<summary[^>]*>(.*?)</summary>(.*?)</details>", body, re.S):
        q, a = strip_tags(q), strip_tags(a)
        if q and a:
            items.append({"@type": "Question", "name": q,
                          "acceptedAnswer": {"@type": "Answer", "text": a}})
    return items


ORG = {
    "@type": "Organization",
    "@id": BASE + "/#org",
    "name": SITE["name"],
    "legalName": SITE["legal_name"],
    "url": BASE + "/",
    "logo": BASE + "/favicon.png",
    "email": SITE["email"],
    "telephone": SITE["phone"],
    "address": {"@type": "PostalAddress", "addressLocality": SITE["city"],
                "addressRegion": SITE["region"], "addressCountry": "CL"},
    "sameAs": SITE["same_as"],
    "parentOrganization": {"@type": "Organization", "name": "Contador APR", "url": "https://www.contadorapr.cl/"},
}
APP = {
    "@type": "SoftwareApplication",
    "@id": BASE + "/#app",
    "name": "NexoAPR",
    "url": BASE + "/",
    "applicationCategory": "BusinessApplication",
    "applicationSubCategory": "ERP para comités de agua potable rural",
    "operatingSystem": "Web",
    "description": SITE["description"],
    "inLanguage": "es-CL",
    "publisher": {"@id": BASE + "/#org"},
    "featureList": ["Socios y arranques", "Lecturas y producción", "Facturación y cobranza", "Tesorería, caja y banco",
                    "Compras e inventario", "Contabilidad, balance de 8 columnas e informe DOH", "Migración controlada"],
}
WEBSITE = {"@type": "WebSite", "@id": BASE + "/#website", "url": BASE + "/",
           "name": SITE["name"], "inLanguage": "es-CL", "publisher": {"@id": BASE + "/#org"}}

TEMPLATE = read(os.path.join(ROOT, "templates", "base.html"))
CHROME = ""
NAV_KEYS = ["modulos", "migracion", "seguridad", "blog", "demo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def render(*, path, title, description, content, og_type="website", robots="", graph_extra=(), image=None, nav=""):
    url = BASE + path
    graph = [ORG, WEBSITE, APP] + list(graph_extra)
    robots_meta = '<meta name="robots" content="noindex, nofollow">' if robots == "noindex" else \
        '<meta name="robots" content="index, follow, max-image-preview:large">'
    adsense = ""
    if False:
        adsense = ('<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='
                   + SITE["adsense_client"] + '" crossorigin="anonymous"></script>')
    rep = {
        "title": esc(title), "description": esc(description), "url": esc(url),
        "og_type": og_type, "og_image": esc(BASE + (image or SITE["og_image"])),
        "robots_meta": robots_meta, "base": BASE, "build": BUILD, "year": YEAR,
        "jsonld": json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/"),
        "adsense": adsense, "chrome": CHROME, "body_class": nav or "page",
        "photo_credits": SITE.get("photo_credits", ""),
    }
    for k in NAV_KEYS:
        rep["nav_" + k] = ' aria-current="page"' if nav == k else ""
    out = TEMPLATE
    for k, v in rep.items():
        out = out.replace("{{" + k + "}}", v)
    out = out.replace("{{content}}", content)
    return out.replace("{{year}}", YEAR)


def fmt_date(d):
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def post_cards(posts, heading_tag="h3"):
    li = []
    for p in posts:
        img = p.get("image") or SITE["og_image"]
        li.append(
            f'<li><a class="post-card" href="{p["path"]}"><img src="{esc(img)}" alt="" loading="lazy" width="640" height="360">'
            f'<span class="post-card__body"><time datetime="{p["date"]}">{fmt_date(p["d"])}</time>'
            f'<{heading_tag}>{esc(p["title"])}</{heading_tag}><p>{esc(p["description"])}</p></span></a></li>')
    return '<ul class="post-list">' + "".join(li) + "</ul>"


def load_news():
    path = os.path.join(ROOT, "content", "news.json")
    if not os.path.exists(path):
        return []
    items = json.load(open(path, encoding="utf-8"))
    for n in items:
        for req in ("date", "title", "summary", "why", "source", "url"):
            if not n.get(req):
                sys.exit(f"ERROR: noticia sin campo '{req}': {n.get('title')}")
        n["d"] = dt.date.fromisoformat(n["date"])
    items.sort(key=lambda n: n["d"], reverse=True)
    return items


def news_html(items, layout="grid"):
    out = []
    for n in items:
        guide = f' <a href="{esc(n["guide"])}">Leer nuestra guía</a>.' if n.get("guide") else ""
        date = f'<time datetime="{n["date"]}">{fmt_date(n["d"])}</time>'
        meta = f'<p class="news__meta"><span class="news__tag">{esc(n.get("tag",""))}</span><span>{esc(n.get("region",""))}</span>' + \
               ("" if layout == "list" else f"<span>{date}</span>") + "</p>"
        out.append(
            '<article class="news">' + (f'<p class="news__date">{date}</p>' if layout == "list" else "") + meta +
            f'<h3><a href="{esc(n["url"])}" rel="noopener">{esc(n["title"])}</a></h3>'
            f'<p>{esc(n["summary"])}</p>'
            f'<p class="news__why"><strong>Para su comité:</strong> {esc(n["why"])}{guide}</p>'
            f'<p class="news__src">Fuente: <a href="{esc(n["url"])}" rel="noopener">{esc(n["source"])}</a></p></article>')
    cls = "news-list" if layout == "list" else "news-grid"
    return f'<div class="{cls}">' + "".join(out) + "</div>"


def load_posts():
    posts = []
    d = os.path.join(ROOT, "content", "posts")
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not fn.endswith(".html"):
            continue
        p = parse(os.path.join(d, fn))
        for req in ("title", "description", "date", "slug"):
            if not p.get(req):
                sys.exit(f"ERROR: {fn} sin campo '{req}'")
        if p.get("draft", "").lower() in ("true", "si", "sí", "1"):
            continue
        p["d"] = dt.date.fromisoformat(p["date"])
        if p["d"] > NOW.date():
            continue  # fecha futura: se publica cuando llegue la fecha (al reconstruir)
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", p["slug"]):
            sys.exit(f"ERROR: slug inválido en {fn}")
        p["path"] = f"/{p['d'].year:04d}/{p['d'].month:02d}/{p['slug']}.html"
        posts.append(p)
    posts.sort(key=lambda p: (p["d"], p["slug"]), reverse=True)
    paths = [p["path"] for p in posts]
    if len(paths) != len(set(paths)):
        sys.exit("ERROR: hay dos artículos con la misma URL")
    return posts


def fill_blocks(body, posts, news):
    def rep_news(m):
        arg = m.group(1)
        if arg == "todas":
            return news_html(news, "list") if news else "<p>Pronto publicaremos las primeras noticias.</p>"
        return news_html(news[:int(arg)]) if news else ""
    body = re.sub(r"<!-- NOTICIAS:(\w+) -->", rep_news, body)
    body = re.sub(r"<!-- GUIAS:(\d+) -->",
                  lambda m: post_cards(posts[:int(m.group(1))]) if posts else "<p>Pronto publicaremos las primeras guías.</p>", body)
    return body


WA_ART = "https://wa.me/56940144218?text=Hola%2C%20le%C3%AD%20una%20gu%C3%ADa%20en%20nexoapr.cl%20y%20quiero%20conocer%20el%20sistema."


def build():
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    shutil.copytree(os.path.join(ROOT, "static"), DIST)
    posts = load_posts()
    news = load_news()
    sitemap = []

    # Páginas fijas
    for fn in sorted(os.listdir(os.path.join(ROOT, "content", "pages"))):
        p = parse(os.path.join(ROOT, "content", "pages", fn))
        body = fill_blocks(p["body"], posts, news)
        extra = [{"@type": "WebPage", "@id": BASE + p["path"] + "#webpage", "url": BASE + p["path"],
                  "name": p["title"], "description": p["description"], "inLanguage": "es-CL",
                  "isPartOf": {"@id": BASE + "/#website"}, "about": {"@id": BASE + "/#org"}}]
        faq = faq_items(body)
        if faq:
            extra.append({"@type": "FAQPage", "@id": BASE + p["path"] + "#faq", "mainEntity": faq})
        write(p["path"] if p["path"] != "/" else "/index.html",
              render(path=p["path"], title=p["title"], description=p["description"],
                     content=body, robots=p.get("robots", ""), graph_extra=extra, nav=p.get("nav", "")))
        if p.get("robots") != "noindex":
            sitemap.append((p["path"], p.get("updated", "")))

    # Artículos
    for p in posts:
        img = p.get("image") or SITE["og_image"]
        faq = faq_items(p["body"])
        rel = [q for q in posts if q is not p][:3]
        content = (
            '<header class="page-head"><div class="wrap">'
            '<p class="crumbs"><a href="/">Inicio</a> / <a href="/blog/">Guías</a></p>'
            f'<h1>{esc(p["title"])}</h1>'
            f'<p class="article__meta">{esc(p.get("category", "Gestión APR"))}. Por {esc(SITE["author"])}, '
            f'<time datetime="{p["date"]}">{fmt_date(p["d"])}</time>.</p>'
            '</div></header>'
            '<div class="article"><div class="wrap">'
            f'<article class="prose">{p["body"]}</article>'
            '<aside class="article__aside"><div class="cta-box">'
            '<h2>Vea NexoAPR con datos de un comité</h2>'
            '<p>Lecturas, facturación, cobranza, caja, contabilidad e informe DOH en una sola plataforma web.</p>'
            '<a class="primary" href="/p/demostracion.html">Solicitar demostración</a>'
            f'<a class="secondary" href="{WA_ART}">Escribir por WhatsApp</a>'
            '</div></aside></div></div>')
        if rel:
            content += ('<section class="section"><div class="wrap"><div class="section__head"><h2>Siga leyendo</h2></div>'
                        + post_cards(rel) + '</div></section>')
        extra = [{"@type": "BlogPosting", "@id": BASE + p["path"] + "#article", "mainEntityOfPage": BASE + p["path"],
                  "headline": p["title"], "description": p["description"], "datePublished": p["date"],
                  "dateModified": p.get("updated") or p["date"], "inLanguage": "es-CL",
                  "image": BASE + img, "author": {"@type": "Organization", "name": SITE["author"], "url": BASE + "/"},
                  "publisher": {"@id": BASE + "/#org"}, "keywords": p.get("keywords", "")},
                 {"@type": "BreadcrumbList", "itemListElement": [
                     {"@type": "ListItem", "position": 1, "name": "Inicio", "item": BASE + "/"},
                     {"@type": "ListItem", "position": 2, "name": "Guías", "item": BASE + "/blog/"},
                     {"@type": "ListItem", "position": 3, "name": p["title"], "item": BASE + p["path"]}]}]
        if faq:
            extra.append({"@type": "FAQPage", "@id": BASE + p["path"] + "#faq", "mainEntity": faq})
        write(p["path"], render(path=p["path"], title=f'{p["title"]} | NexoAPR', description=p["description"],
                                content=content, og_type="article", graph_extra=extra, image=img, nav="blog"))
        sitemap.append((p["path"], p.get("updated") or p["date"]))

    # Listado de guías
    blog_body = ('<header class="page-head"><div class="wrap"><p class="crumbs"><a href="/">Inicio</a> / Guías</p>'
                 '<h1>Guías de gestión para APR y SSR</h1>'
                 '<p class="lead">Gestión digital del comité: lecturas, facturación, cobranza, tesorería, contabilidad, informe DOH '
                 'y tecnología aplicada al agua potable rural en Chile.</p></div></header>'
                 '<section class="section"><div class="wrap">'
                 + (post_cards(posts, "h2") if posts else "<p>Pronto publicaremos las primeras guías.</p>")
                 + "</div></section>")
    write("/blog/index.html", render(path="/blog/", title="Guías de gestión para APR y SSR | NexoAPR",
                                     description="Guías sobre gestión digital de comités APR y SSR: lecturas, facturación, cobranza, tesorería, contabilidad e informe DOH.",
                                     content=blog_body, nav="blog",
                                     graph_extra=[{"@type": "Blog", "@id": BASE + "/blog/#blog", "url": BASE + "/blog/",
                                                   "name": "Guías NexoAPR", "publisher": {"@id": BASE + "/#org"}}]))
    sitemap.append(("/blog/", posts[0]["date"] if posts else ""))

    # 404
    write("/404.html", render(path="/404.html", title="Página no encontrada | NexoAPR",
                              description="La página que busca no existe.", robots="noindex",
                              content='<header class="page-head"><div class="wrap"><h1>No encontramos esa página</h1>'
                                      '<p class="lead">Puede volver al <a href="/">inicio</a>, revisar nuestros '
                                      '<a href="/p/modulos.html">módulos</a> o leer las <a href="/blog/">guías</a>.</p></div></header>'))

    # sitemap.xml
    urls = []
    for path, lastmod in sitemap:
        lm = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        urls.append(f"<url><loc>{BASE}{path}</loc>{lm}</url>")
    write("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(urls) + "</urlset>\n")

    # RSS
    items = []
    for p in posts[:20]:
        pub = format_datetime(dt.datetime.combine(p["d"], dt.time(12, 0), dt.timezone.utc))
        items.append(f"<item><title>{esc(p['title'])}</title><link>{BASE}{p['path']}</link>"
                     f"<guid>{BASE}{p['path']}</guid><pubDate>{pub}</pubDate>"
                     f"<description>{esc(p['description'])}</description></item>")
    write("/rss.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
          f"<title>NexoAPR - Guías</title><link>{BASE}/blog/</link>"
          f"<description>{esc(SITE['description'])}</description><language>es-cl</language>"
          + "".join(items) + "</channel></rss>\n")

    print(f"OK: {len(sitemap)} URLs en sitemap, {len(posts)} guías, {len(news)} noticias -> dist/")


if __name__ == "__main__":
    build()
