"""Jumeau numerique du panneau : passerelle + simulateur navigateur.

Lancer :  python3 server.py
Ouvrir :  http://localhost:8080

Endpoints :
  /            page de simulation du panneau LED
  /frame       tampon de pixels courant (base64 RGB) pour le simulateur
  /flight      JSON compact consomme par l'ESP32 (vol + priere + ecran a
               afficher)
  /flight/full JSON complet du vol, pour mise au point
  /prieres     JSON complet de la priere courante, pour mise au point
  /snapshot.png capture PNG du panneau
"""

import base64
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import panel
from composition import compact_flight, render_screen
from passerelle import Gateway

HERE = os.path.dirname(os.path.abspath(__file__))

PAGE = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<title>Jumeau numerique - panneau LED 128x32</title>
<style>
 body { margin:0; background:#111214; color:#c9c7c2; font:14px ui-monospace,Menlo,Consolas,monospace; }
 .wrap { max-width:1100px; margin:0 auto; padding:24px; }
 h1 { font-size:15px; font-weight:500; color:#8d8b86; letter-spacing:2px; text-transform:uppercase; }
 .case { background:#1a1a1d; border:1px solid #2a2a2e; border-radius:10px; padding:14px; }
 canvas { width:100%; display:block; image-rendering:pixelated; border-radius:4px; background:#000; }
 .meta { display:flex; gap:24px; flex-wrap:wrap; margin-top:18px; }
 .card { background:#1a1a1d; border:1px solid #2a2a2e; border-radius:10px; padding:14px; flex:1; min-width:280px; }
 .card h2 { font-size:12px; color:#8d8b86; letter-spacing:1px; text-transform:uppercase; margin:0 0 10px; font-weight:500; }
 pre { margin:0; white-space:pre-wrap; word-break:break-all; color:#e0a03c; font-size:13px; }
 .dot { display:inline-block; width:8px; height:8px; border-radius:50%; background:#3b8; margin-right:6px; }
 .off { background:#a44; }
 label { color:#8d8b86; margin-right:10px; }
</style></head><body><div class="wrap">
<h1>Jumeau numerique &mdash; panneau 128 x 32</h1>
<div class="case"><canvas id="led" width="1024" height="256"></canvas></div>
<div class="meta">
  <div class="card"><h2>Etat de la passerelle</h2><pre id="status">...</pre></div>
  <div class="card"><h2>JSON envoye a l'ESP32 (/flight)</h2><pre id="json">...</pre></div>
</div>
<p style="color:#6c6a66; font-size:12px; margin-top:18px;">
  Le rendu ci-dessus est calcule par panel.py, exactement la mise en page que le firmware reproduit sur le vrai panneau.
</p>
</div>
<script>
const cv = document.getElementById('led'), ctx = cv.getContext('2d');
const W = 128, H = 32, CELL = 8;
function draw(bytes) {
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, cv.width, cv.height);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const i = (y * W + x) * 3;
      const r = bytes[i], g = bytes[i+1], b = bytes[i+2];
      const on = r + g + b > 12;
      ctx.fillStyle = on ? `rgb(${r},${g},${b})` : '#141416';
      ctx.beginPath();
      ctx.arc(x * CELL + CELL/2, y * CELL + CELL/2, on ? CELL*0.40 : CELL*0.22, 0, 6.2832);
      ctx.fill();
    }
  }
}
async function tick() {
  try {
    const res = await fetch('/frame', {cache:'no-store'});
    const data = await res.json();
    const bin = atob(data.rgb);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    draw(bytes);
    const live = data.status.source === 'direct' && !data.status.error;
    document.getElementById('status').innerHTML =
      '<span class="dot' + (live ? '' : ' off') + '"></span>' +
      'source : ' + data.status.source +
      (data.status.error ? '\\n' + data.status.error : '') +
      '\\ndernier sondage : ' + (data.status.last_poll ? new Date(data.status.last_poll*1000).toLocaleTimeString('fr-FR') : '-');
    document.getElementById('json').textContent = JSON.stringify(data.flight, null, 1);
  } catch (e) { /* le serveur redemarre peut-etre */ }
}
setInterval(tick, 100); tick();
</script></body></html>
"""


class Handler(BaseHTTPRequestHandler):
    gateway = None
    config = {}

    def log_message(self, *args):
        pass

    def _send(self, code, content_type, body):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        elapsed = time.time() - self.gateway.started
        if path == "/":
            self._send(200, "text/html; charset=utf-8", PAGE)
        elif path == "/frame":
            frame, ecran, donnees = render_screen(
                self.gateway, self.config, elapsed)
            payload = {
                "w": panel.WIDTH, "h": panel.HEIGHT,
                "rgb": base64.b64encode(frame.to_rgb_bytes()).decode("ascii"),
                "flight": compact_flight(donnees[0], donnees[1], ecran,
                                         donnees[2], donnees[3],
                                         donnees[4], donnees[5],
                                         self.gateway.current_audio()),
                "status": self.gateway.status(),
            }
            self._send(200, "application/json", json.dumps(payload))
        elif path == "/flight":
            (ecran, flight, prieres, meteo, heure, rang,
             usage) = self.gateway.screen()
            self._send(200, "application/json",
                       json.dumps(compact_flight(
                           flight, prieres, ecran, meteo, heure, rang, usage,
                           self.gateway.current_audio())))
        elif path == "/flight/full":
            self._send(200, "application/json",
                       json.dumps(self.gateway.current() or {}, default=str))
        elif path == "/prieres":
            self._send(200, "application/json",
                       json.dumps(self.gateway.current_prieres() or {}, default=str))
        elif path == "/meteo":
            self._send(200, "application/json",
                       json.dumps(self.gateway.current_meteo() or {}, default=str))
        elif path == "/snapshot.png":
            frame, _, _ = render_screen(self.gateway, self.config, elapsed)
            self._send(200, "image/png", frame.to_png_bytes(scale=6))
        else:
            self._send(404, "text/plain", "introuvable")


def main():
    with open(os.path.join(HERE, "config.json"), "r", encoding="utf-8") as handle:
        config = json.load(handle)

    gateway = Gateway(config)
    threading.Thread(target=gateway.run, daemon=True).start()

    Handler.gateway = gateway
    Handler.config = config
    port = config.get("http_port", 8080)
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print("Panneau simule      : http://localhost:%d" % port)
    print("JSON pour l'ESP32   : http://localhost:%d/flight" % port)
    print("Mode demo           : %s" % ("oui" if config.get("demo_mode") else "non"))
    print("Mosquee             : %s" % (config.get("mosquee_slug") or "aucune"))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\narret")


if __name__ == "__main__":
    main()
