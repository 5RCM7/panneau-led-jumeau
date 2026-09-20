"""Genere arabe.py et firmware/arabe.h : les noms de prieres en arabe.

    python3 export_arabe.py

La police 5x7 du panneau est ASCII pure et le restera : l'arabe demande des
formes contextuelles et une ecriture de droite a gauche, ce qu'une table de
glyphes fixes ne sait pas faire. Les six noms sont donc des silhouettes,
comme les icones meteo, rendues une fois pour toutes depuis une vraie police.

Ce script n'est utile qu'en cas de changement de hauteur ou de police. Il
demande Pillow, arabic-reshaper et python-bidi ; le panneau, lui, n'a besoin
de rien de tout ca puisqu'il lit les fichiers generes.

    pip install Pillow arabic-reshaper python-bidi
"""

import os
import sys

HAUTEUR = 16      # en deca, les points des lettres se confondent
SEUIL = 110       # un pixel LED est allume ou eteint, pas de gris
POLICES = (r"C:\Windows\Fonts\arialbd.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "/Library/Fonts/Arial Bold.ttf")

# Cle latine -> mot arabe. Les cles suivent horaires.NOMS, plus la Joumoua.
MOTS = (
    ("FAJR", "\u0627\u0644\u0641\u062c\u0631"),
    ("DOHR", "\u0627\u0644\u0638\u0647\u0631"),
    ("ASR", "\u0627\u0644\u0639\u0635\u0631"),
    ("MAGHREB", "\u0627\u0644\u0645\u063a\u0631\u0628"),
    ("ICHA", "\u0627\u0644\u0639\u0634\u0627\u0621"),
    ("JOUMOUA", "\u0627\u0644\u062c\u0645\u0639\u0629"),
)

HERE = os.path.dirname(os.path.abspath(__file__))


def _rendu(mot, police):
    """Mot arabe -> liste de chaines de '.' et '#', hauteur HAUTEUR."""
    import arabic_reshaper
    from bidi.algorithm import get_display
    from PIL import Image, ImageDraw, ImageFont

    forme = get_display(arabic_reshaper.reshape(mot))
    font = ImageFont.truetype(police, HAUTEUR)
    boite = font.getbbox(forme)
    largeur = max(1, boite[2] - boite[0] + 2)
    image = Image.new("L", (largeur, HAUTEUR + 8), 0)
    ImageDraw.Draw(image).text((1 - boite[0], 0), forme, fill=255, font=font)

    pixels = image.load()
    lignes = ["".join("#" if pixels[x, y] > SEUIL else "."
                      for x in range(image.width))
              for y in range(image.height)]
    # on rogne les lignes et colonnes vides, puis on cale sur HAUTEUR
    hautes = [i for i, l in enumerate(lignes) if "#" in l]
    if not hautes:
        return ["." * 4] * HAUTEUR
    lignes = lignes[hautes[0]:hautes[-1] + 1]
    colonnes = [x for x in range(len(lignes[0]))
                if any(l[x] == "#" for l in lignes)]
    gauche, droite = colonnes[0], colonnes[-1]
    lignes = [l[gauche:droite + 1] for l in lignes]
    while len(lignes) < HAUTEUR:
        lignes.append("." * len(lignes[0]))
    return lignes[:HAUTEUR]


def main():
    police = next((p for p in POLICES if os.path.exists(p)), None)
    if not police:
        print("aucune police trouvee parmi :", ", ".join(POLICES))
        return 1
    print("police :", os.path.basename(police))

    try:
        rendus = [(cle, _rendu(mot, police)) for cle, mot in MOTS]
    except ImportError as exc:
        print("dependance manquante :", exc)
        print("pip install Pillow arabic-reshaper python-bidi")
        return 1

    py = ['"""Noms de prieres en arabe, en silhouettes.',
          "",
          "GENERE par export_arabe.py. Ne pas editer a la main.",
          "",
          "La police 5x7 est ASCII pure : l'arabe demande des formes",
          "contextuelles et une ecriture de droite a gauche, qu'une table de",
          "glyphes ne sait pas rendre. Ces mots sont donc des images, deja",
          "mises en forme et deja retournees.",
          '"""',
          "",
          "HAUTEUR = %d" % HAUTEUR,
          "",
          "MOTS = {"]
    for cle, lignes in rendus:
        py.append('    "%s": (' % cle)
        for ligne in lignes:
            py.append('        "%s",' % ligne)
        py.append("    ),")
    py.append("}")
    py.append("")
    py.append("")
    py.append("def mot(nom):")
    py.append('    """Silhouette d\'un nom de priere, ou None si inconnu."""')
    py.append("    return MOTS.get(nom)")
    py.append("")
    py.append("")
    py.append("def largeur(nom):")
    py.append('    """Largeur en pixels, 0 si le nom est inconnu."""')
    py.append("    motif = MOTS.get(nom)")
    py.append("    return len(motif[0]) if motif else 0")
    py.append("")
    chemin_py = os.path.join(HERE, "arabe.py")
    with open(chemin_py, "w", encoding="ascii") as handle:
        handle.write("\n".join(py))

    c = ["// arabe.h - noms de prieres en arabe, en silhouettes",
         "//",
         "// GENERE par export_arabe.py. Ne pas editer a la main.",
         "//",
         "// Jumeau d'arabe.py. La police 5x7 est ASCII pure : l'arabe demande",
         "// des formes contextuelles et une ecriture de droite a gauche.",
         "//",
         "// Inclus depuis panneau_vols.ino AVANT ecran_horaires.h.",
         "",
         "#ifndef ARABE_H",
         "#define ARABE_H",
         "",
         "static const int16_t ARABE_H_PX = %d;" % HAUTEUR,
         ""]
    for cle, lignes in rendus:
        c.append("static const char *ARABE_%s[ARABE_H_PX] = {" % cle)
        for ligne in lignes:
            c.append('    "%s",' % ligne)
        c.append("};")
        c.append("")
    c.append("struct MotArabe { const char *nom; const char **motif;"
             " int16_t largeur; };")
    c.append("")
    c.append("static const MotArabe ARABE_MOTS[] = {")
    for cle, lignes in rendus:
        c.append('    {"%s", ARABE_%s, %d},' % (cle, cle, len(lignes[0])))
    c.append("};")
    c.append("static const int8_t ARABE_COUNT = %d;" % len(rendus))
    c.append("")
    c.append("// Silhouette d'un nom de priere, ou nullptr si inconnu.")
    c.append("static const MotArabe *arabePour(const char *nom) {")
    c.append("  for (int8_t i = 0; i < ARABE_COUNT; i++)")
    c.append("    if (strcmp(ARABE_MOTS[i].nom, nom) == 0)"
             " return &ARABE_MOTS[i];")
    c.append("  return nullptr;")
    c.append("}")
    c.append("")
    c.append("#endif  // ARABE_H")
    c.append("")
    chemin_c = os.path.join(HERE, "firmware", "arabe.h")
    with open(chemin_c, "w", encoding="ascii") as handle:
        handle.write("\n".join(c))

    for cle, lignes in rendus:
        print("  %-8s %2d x %2d px" % (cle, len(lignes[0]), len(lignes)))
    print("\narabe.py et firmware/arabe.h ecrits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
