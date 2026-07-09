/**
 * WTBS suggestion intake + daily email digest — Cloudflare Worker.
 *
 * fetch():      receives a suggestion from the site widget, validates it, and
 *               appends it to a KV queue. Nothing is emailed immediately.
 * scheduled():  runs once a day (Cron Trigger). Reads the queue, emails you one
 *               digest of everything that came in, then clears the queue.
 *
 * Bindings / secrets (see wrangler.toml):
 *   SUGGESTIONS     KV namespace (queue storage)                     [binding]
 *   RESEND_API_KEY  Resend API key                                   [secret]
 *   MAIL_TO         your inbox, e.g. you@example.com                 [var]
 *   MAIL_FROM       verified sender, e.g. wtbs@yourdomain.com        [var]
 *   ALLOW_ORIGIN    site origin allowed to POST, e.g. https://wtbs.pages.dev [var]
 */

const TYPES = ["spelling", "grammar", "capitalization", "punctuation", "hyperlink", "other"];
const QUEUE_KEY = "pending";

function cors(o) {
  return { "Access-Control-Allow-Origin": o, "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type" };
}
function json(status, obj, o) {
  return new Response(JSON.stringify(obj), { status,
    headers: { "Content-Type": "application/json", ...cors(o) } });
}
const esc = s => String(s || "").replace(/[<>&]/g, c => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]));

export default {
  // ---- intake ----
  async fetch(request, env) {
    const origin = env.ALLOW_ORIGIN || "*";
    if (request.method === "OPTIONS") return new Response(null, { headers: cors(origin) });
    if (request.method !== "POST") return json(405, { error: "method" }, origin);
    if (env.ALLOW_ORIGIN && request.headers.get("Origin") !== env.ALLOW_ORIGIN)
      return json(403, { error: "forbidden" }, origin);

    let d;
    try { d = await request.json(); } catch { return json(400, { error: "bad json" }, origin); }
    const name = String(d.name || "").trim(), email = String(d.email || "").trim();
    if (!name || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email))
      return json(400, { error: "name and valid email required" }, origin);
    if (!d.episode || !TYPES.includes(d.type)) return json(400, { error: "missing episode/type" }, origin);
    if ((String(d.original).length + String(d.suggested).length) > 4000)
      return json(400, { error: "too long" }, origin);

    const rec = {
      at: new Date().toISOString(),
      episode: d.episode, title: d.title, type: d.type,
      original: String(d.original || "").slice(0, 2000),
      suggested: String(d.suggested || "").slice(0, 2000),
      url: String(d.url || "").slice(0, 500), note: String(d.note || "").slice(0, 1000),
      anchor_idx: d.anchor_idx, page: d.page, name, email,
    };
    const cur = JSON.parse((await env.SUGGESTIONS.get(QUEUE_KEY)) || "[]");
    cur.push(rec);
    await env.SUGGESTIONS.put(QUEUE_KEY, JSON.stringify(cur));
    return json(200, { ok: true, queued: cur.length }, origin);
  },

  // ---- daily digest ----
  async scheduled(event, env, ctx) {
    ctx.waitUntil((async () => {
      const items = JSON.parse((await env.SUGGESTIONS.get(QUEUE_KEY)) || "[]");
      if (!items.length) return;

      const rows = items.map(s => `
        <div style="border-top:2px solid #000;padding:12px 0">
          <div style="font-family:monospace;font-size:12px;text-transform:uppercase">
            [${esc(s.type)}] ${esc(s.title || s.episode)} · turn ${esc(s.anchor_idx)}</div>
          ${s.original ? `<p style="margin:6px 0"><b>Original:</b> ${esc(s.original)}</p>` : ""}
          ${s.suggested ? `<p style="margin:6px 0"><b>Suggested:</b> ${esc(s.suggested)}</p>` : ""}
          ${s.url ? `<p style="margin:6px 0"><b>Link:</b> ${esc(s.url)}</p>` : ""}
          ${s.note ? `<p style="margin:6px 0"><b>Note:</b> ${esc(s.note)}</p>` : ""}
          <p style="margin:6px 0;color:#555;font-size:13px">— ${esc(s.name)} (${esc(s.email)})
             · <a href="${esc(s.page)}">${esc(s.page)}</a> · ${esc(s.at)}</p>
        </div>`).join("");

      const res = await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: { "Authorization": `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          from: env.MAIL_FROM, to: env.MAIL_TO,
          subject: `WTBS — ${items.length} edit suggestion${items.length > 1 ? "s" : ""}`,
          html: `<h2 style="font-family:Helvetica,Arial">${items.length} suggestion${items.length > 1 ? "s" : ""} today</h2>${rows}`,
        }),
      });
      // Only clear the queue if the email actually sent (else retry tomorrow).
      if (res.ok) await env.SUGGESTIONS.put(QUEUE_KEY, "[]");
    })());
  },
};
