// Worker de nexoapr.cl
// - nexoapr.cl redirige a www.nexoapr.cl (una sola versión para Google).
// - POST /api/demo: guarda la solicitud de demostración en D1 y envía un aviso por correo.
// - Archivos con extensión: los entrega la capa de assets (html_handling: none), con _redirects y _headers.
// - Carpetas ("/", "/blog/") sirven su index.html; rutas sin barra final redirigen a la carpeta.
import { EmailMessage } from "cloudflare:email";

const CARGOS = ["Presidente/a", "Tesorero/a", "Secretario/a", "Administrativo/a", "Contador/a", "Otro"];
const SISTEMAS = ["Planillas Excel", "Otro sistema", "Cuadernos o papel", "Una mezcla", "No estoy seguro"];

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

function clean(v, max) {
  return String(v ?? "").replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "").trim().slice(0, max);
}

async function sha256(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function b64(text) {
  const bytes = new TextEncoder().encode(text);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

function mime({ from, to, subject, body }) {
  const id = `<${crypto.randomUUID()}@nexoapr.cl>`;
  const lines = b64(body).match(/.{1,76}/g).join("\r\n");
  return [
    `From: Sitio NexoAPR <${from}>`,
    `To: <${to}>`,
    `Subject: =?UTF-8?B?${b64(subject)}?=`,
    `Date: ${new Date().toUTCString()}`,
    `Message-ID: ${id}`,
    "MIME-Version: 1.0",
    "Content-Type: text/plain; charset=utf-8",
    "Content-Transfer-Encoding: base64",
    "",
    lines,
  ].join("\r\n");
}

async function demo(request, env) {
  const origin = request.headers.get("origin") || "";
  if (origin && !/^https:\/\/(www\.)?nexoapr\.cl$|^https:\/\/[a-z0-9-]+\.contadorvaldivialosrios\.workers\.dev$/.test(origin)) {
    return json({ ok: false, error: "Origen no permitido." }, 403);
  }
  let d;
  try { d = await request.json(); } catch { return json({ ok: false, error: "Solicitud inválida." }, 400); }
  if (clean(d.web, 100)) return json({ ok: true }); // trampa para robots

  const correo = clean(d.correo, 120);
  const s = {
    nombre: clean(d.nombre, 120), cargo: CARGOS.includes(d.cargo) ? d.cargo : null,
    telefono: clean(d.telefono, 40), correo: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo) ? correo : null,
    comite: clean(d.comite, 160), comuna: clean(d.comuna, 80),
    socios: Number.isFinite(+d.socios) && d.socios !== "" ? Math.max(0, Math.min(50000, Math.round(+d.socios))) : null,
    sistema: SISTEMAS.includes(d.sistema_actual) ? d.sistema_actual : "No estoy seguro",
    mensaje: clean(d.mensaje, 4000),
  };
  const faltan = [];
  if (s.nombre.length < 2) faltan.push("nombre");
  if (s.telefono.replace(/\D/g, "").length < 8) faltan.push("telefono");
  if (s.comite.length < 2) faltan.push("comite");
  if (faltan.length) return json({ ok: false, error: "Faltan datos.", campos: faltan }, 422);

  const ip = request.headers.get("cf-connecting-ip") || "";
  const ipHash = (await sha256("nexoapr:" + ip)).slice(0, 32);
  const recientes = await env.DB.prepare(
    "SELECT COUNT(*) AS n FROM demos WHERE ip_hash = ? AND creado > datetime('now','-1 hour')").bind(ipHash).first();
  if ((recientes?.n || 0) >= 5) {
    return json({ ok: false, error: "Recibimos varias solicitudes seguidas. Escríbanos por WhatsApp." }, 429);
  }

  const res = await env.DB.prepare(
    "INSERT INTO demos (nombre, cargo, telefono, correo, comite, comuna, socios, sistema_actual, mensaje, origen, ip_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?)")
    .bind(s.nombre, s.cargo, s.telefono, s.correo, s.comite, s.comuna || null, s.socios, s.sistema, s.mensaje || null,
      clean(request.headers.get("referer"), 200), ipHash).run();
  const id = res.meta?.last_row_id;

  let enviado = false;
  try {
    const tel = s.telefono.replace(/\D/g, "");
    const wa = tel.length >= 8 ? `https://wa.me/${tel.startsWith("56") ? tel : "56" + tel.replace(/^0+/, "")}` : "";
    const body = [
      `Nueva solicitud de demostración desde nexoapr.cl (N° ${id})`,
      "",
      `Nombre: ${s.nombre}`,
      `Cargo: ${s.cargo || "-"}`,
      `Teléfono / WhatsApp: ${s.telefono}`,
      `Correo: ${s.correo || "-"}`,
      `Comité: ${s.comite}`,
      `Comuna: ${s.comuna || "-"}`,
      `Socios: ${s.socios ?? "-"}`,
      `Gestión actual: ${s.sistema}`,
      "",
      "Mensaje:",
      s.mensaje || "-",
      "",
      wa ? `Responder por WhatsApp: ${wa}` : "",
      "",
      "Aviso automático del formulario de nexoapr.cl. La solicitud quedó guardada en la base nexoapr-demos.",
    ].join("\n");
    const raw = mime({ from: env.AVISO_DESDE, to: "contadorvaldivialosrios@gmail.com",
      subject: `Demo NexoAPR: ${s.comite}`, body });
    await env.AVISO.send(new EmailMessage(env.AVISO_DESDE, "contadorvaldivialosrios@gmail.com", raw));
    enviado = true;
    await env.DB.prepare("UPDATE demos SET correo_enviado = 1 WHERE id = ?").bind(id).run();
  } catch (e) {
    console.log("Fallo envío de correo", String(e));
  }
  return json({ ok: true, id, correo: enviado });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname === "nexoapr.cl") {
      url.hostname = "www.nexoapr.cl";
      return Response.redirect(url.toString(), 301);
    }
    if (url.pathname === "/api/demo") {
      if (request.method !== "POST") return json({ ok: false, error: "Método no permitido." }, 405);
      try { return await demo(request, env); }
      catch (e) { console.log("Error solicitud", String(e)); return json({ ok: false, error: "No pudimos guardar la solicitud." }, 500); }
    }
    const direct = await env.ASSETS.fetch(request);
    if (direct.status !== 404) return direct;
    if (url.pathname.endsWith("/")) {
      const index = await env.ASSETS.fetch(new Request(new URL(url.pathname + "index.html", url), request));
      if (index.status === 200) return index;
    } else if (!/\.[a-z0-9]+$/i.test(url.pathname)) {
      const folder = await env.ASSETS.fetch(new Request(new URL(url.pathname + "/index.html", url), request));
      if (folder.status === 200) return Response.redirect(new URL(url.pathname + "/" + url.search, url).toString(), 301);
    }
    const notFound = await env.ASSETS.fetch(new Request(new URL("/404.html", url), request));
    return new Response(notFound.body, { status: 404, headers: notFound.headers });
  },
};
