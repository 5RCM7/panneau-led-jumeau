"""Genere apercu.html : une page qui rejoue le panneau, ecran par ecran.

    python3 apercu_html.py

Les images ne sont pas redessinees en JavaScript : le script appelle panel.py
et ecran_prieres.py, puis embarque les pixels obtenus. Ce qui s'affiche dans le
navigateur est donc exactement ce que le moteur produit, et il n'y a pas un
troisieme jumeau a garder en phase. Les horaires viennent de la mosquee
configuree si le cache ou le reseau repondent, sinon d'un jeu de secours.
"""

import json
import os

import apercu_scenes

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = apercu_scenes.FPS


def _encode(frame):
    """Image -> (palette, suite compressee par plages).

    Le panneau est noir a plus de 80 % et n'utilise qu'une poignee de couleurs :
    un codage par plages pese bien moins que les 12288 octets bruts.
    """
    palette, index = ["0,0,0"], {}
    plages = []
    precedent, compte = None, 0
    for i in range(0, len(frame.buf), 3):
        couleur = "%d,%d,%d" % (frame.buf[i], frame.buf[i + 1], frame.buf[i + 2])
        if couleur not in index:
            if couleur == "0,0,0":
                index[couleur] = 0
            else:
                index[couleur] = len(palette)
                palette.append(couleur)
        valeur = index[couleur]
        if valeur == precedent:
            compte += 1
        else:
            if precedent is not None:
                plages.append((compte, precedent))
            precedent, compte = valeur, 1
    plages.append((compte, precedent))
    return palette, plages


def _scenes_encodees():
    sorties = []
    for titre, texte, images in apercu_scenes.scenes():
        codees = []
        palette_globale = ["0,0,0"]
        for frame in images:
            palette, plages = _encode(frame)
            # on fusionne les palettes pour n'en garder qu'une par scene
            correspondance = {}
            for position, couleur in enumerate(palette):
                if couleur not in palette_globale:
                    palette_globale.append(couleur)
                correspondance[position] = palette_globale.index(couleur)
            codees.append([[compte, correspondance[valeur]]
                           for compte, valeur in plages])
        sorties.append({"titre": titre, "texte": texte,
                        "palette": palette_globale, "images": codees})
    return sorties


PAGE = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Panneau LED 128x32</title>
<style>
 :root { color-scheme: dark; }
 body { margin:0; background:#111214; color:#c9c7c2;
        font:14px/1.6 ui-monospace,Menlo,Consolas,monospace; }
 .wrap { max-width:960px; margin:0 auto; padding:24px 16px 48px; }
 h1 { font-size:15px; font-weight:500; color:#8d8b86; letter-spacing:2px;
      text-transform:uppercase; margin:0 0 4px; }
 .sous { color:#6c6a66; font-size:12px; margin:0 0 20px; }
 .case { background:#1a1a1d; border:1px solid #2a2a2e; border-radius:10px;
         padding:14px; }
 canvas { width:100%; display:block; image-rendering:pixelated;
          border-radius:4px; background:#000; }
 .onglets { display:flex; flex-wrap:wrap; gap:6px; margin:18px 0 10px; }
 button { background:#1a1a1d; border:1px solid #2a2a2e; color:#8d8b86;
          border-radius:6px; padding:7px 12px; cursor:pointer;
          font:inherit; font-size:12px; }
 button:hover { border-color:#e0a03c; color:#c9c7c2; }
 button[aria-selected="true"] { background:#e0a03c; border-color:#e0a03c;
                                color:#111214; }
 .note { background:#1a1a1d; border:1px solid #2a2a2e; border-radius:10px;
         padding:12px 14px; color:#9d9b96; font-size:13px; min-height:44px; }
 footer { color:#6c6a66; font-size:12px; margin-top:22px; }
 code { color:#e0a03c; }
</style></head><body><div class="wrap">
<h1>Panneau LED 128 &times; 32</h1>
<p class="sous">Pixels rendus par <code>panel.py</code> et
<code>ecran_prieres.py</code>, rejou&eacute;s tels quels &mdash; la page ne
redessine rien de son c&ocirc;t&eacute;.</p>
<div class="case"><canvas id="led" width="1024" height="256"></canvas></div>
<div class="onglets" id="onglets"></div>
<div class="note" id="note"></div>
<footer>G&eacute;n&eacute;r&eacute; par <code>python3 apercu_html.py</code>.
Les horaires viennent de la mosqu&eacute;e configur&eacute;e dans
<code>config.json</code>.</footer>
</div>
<script>
const SCENES = __SCENES__, FPS = __FPS__;
const W = 128, H = 32, CELL = 8;
const cv = document.getElementById('led'), ctx = cv.getContext('2d');
let scene = 0, image = 0, dernier = 0;

function decode(plages, palette) {
  const out = new Array(W * H); let i = 0;
  for (const [compte, valeur] of plages)
    for (let n = 0; n < compte; n++) out[i++] = palette[valeur];
  return out;
}

function draw(pixels) {
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, cv.width, cv.height);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const couleur = pixels[y * W + x], on = couleur !== '0,0,0';
      ctx.fillStyle = on ? 'rgb(' + couleur + ')' : '#141416';
      ctx.beginPath();
      ctx.arc(x * CELL + CELL / 2, y * CELL + CELL / 2,
              on ? CELL * 0.40 : CELL * 0.22, 0, 6.2832);
      ctx.fill();
    }
  }
}

function choisir(n) {
  scene = n; image = 0;
  document.querySelectorAll('#onglets button').forEach((b, i) =>
    b.setAttribute('aria-selected', i === n));
  document.getElementById('note').textContent = SCENES[n].texte;
  draw(decode(SCENES[n].images[0], SCENES[n].palette));
}

function boucle(t) {
  const s = SCENES[scene];
  if (s.images.length > 1 && t - dernier > 1000 / FPS) {
    dernier = t;
    image = (image + 1) % s.images.length;
    draw(decode(s.images[image], s.palette));
  }
  requestAnimationFrame(boucle);
}

SCENES.forEach((s, i) => {
  const b = document.createElement('button');
  b.textContent = s.titre;
  b.onclick = () => choisir(i);
  document.getElementById('onglets').appendChild(b);
});
choisir(0);
requestAnimationFrame(boucle);
</script></body></html>
"""


def main():
    scenes = _scenes_encodees()
    page = PAGE.replace("__SCENES__", json.dumps(scenes, separators=(",", ":")))
    page = page.replace("__FPS__", str(FPS))
    chemin = os.path.join(HERE, "apercu.html")
    with open(chemin, "w", encoding="utf-8") as handle:
        handle.write(page)
    images = sum(len(s["images"]) for s in scenes)
    print("apercu.html ecrit : %d scenes, %d images, %d Ko"
          % (len(scenes), images, len(page) // 1024))


if __name__ == "__main__":
    main()
