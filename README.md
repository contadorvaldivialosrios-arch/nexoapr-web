# nexoapr.cl

Sitio informativo de NexoAPR (ERP web para comités APR y SSR). La plataforma en sí (nexoapr-app.pages.dev) es otro proyecto y no está aquí.

## Publicación

Worker `nexoapr-web` de Cloudflare con archivos estáticos (`wrangler.jsonc`), en `www.nexoapr.cl` y `nexoapr.cl` (que redirige a www).

```bash
python3 build.py
npx wrangler@4 deploy
```

`.github/workflows/deploy.yml` construye y publica en cada push a `main`, a mano y una vez al día. Usa los secretos `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID`; si el token no es válido, termina con una advertencia y el sitio no cambia.

## Formulario de demostración

`POST /api/demo` (en `worker.js`): valida, guarda en D1 `nexoapr-demos` (tabla `demos`) y avisa por correo a contadorvaldivialosrios@gmail.com desde formulario@nexoapr.cl (Email Routing).

## Estructura

| Carpeta | Contenido |
| --- | --- |
| `content/pages/` | Páginas fijas (campo `path`). |
| `content/posts/` | Guías. URL: `/AAAA/MM/slug.html`. |
| `templates/base.html` | Plantilla general. |
| `static/` | CSS, imágenes, `robots.txt`, `_redirects`, `_headers`. |
| `site.json` | Datos para metadatos y datos estructurados. |

## Cómo publicar una guía

Crear `content/posts/AAAA-MM-DD-slug.html`:

```html
<!--
title: Título de máximo 60 caracteres
description: Descripción de máximo 155 caracteres
date: 2026-10-24
slug: palabras-clave
category: Gestión digital
keywords: palabra clave, secundaria
image: /assets/img/guia-gestion-digital.webp
-->
<p class="capr-lead">Primer párrafo…</p>
<h2>…</h2>
```

Preguntas frecuentes con `<section class="capr-faq"><h2>Preguntas frecuentes</h2><details><summary>…</summary><p>…</p></details></section>`; fuentes con `<p class="capr-sources">Fuentes: …</p>`. `draft: true` oculta; una fecha futura publica ese día.
