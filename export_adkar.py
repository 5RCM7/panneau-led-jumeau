"""Genere adkar.py et firmware/adkar.h depuis adkar_source.py.

    python3 export_adkar.py

Corriger un nom, un sens ou une signification se fait dans adkar_source.py,
puis on relance ce script. Les fichiers generes ne sont jamais edites a la
main.

Meme principe que les noms de prieres : la police 5x7 est ASCII pure, l'arabe
demande des formes contextuelles et une ecriture de droite a gauche. Les mots
sont donc des silhouettes, rendues une fois depuis une vraie police.

    pip install Pillow arabic-reshaper python-bidi
"""

import os

import adkar_source
from export_arabe import HAUTEUR, POLICES, _rendu

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    police = next((p for p in POLICES if os.path.exists(p)), None)
    if not police:
        print("aucune police trouvee parmi :", ", ".join(POLICES))
        return 1
    print("police :", os.path.basename(police))

    try:
        rendus = [(_rendu(arabe, police), latin, sens, detail)
                  for arabe, latin, sens, detail in adkar_source.NOMS]
    except ImportError as exc:
        print("dependance manquante :", exc)
        print("pip install Pillow arabic-reshaper python-bidi")
        return 1

    py = ['"""Adkar : les 99 noms d\'Allah, en silhouettes.',
          "",
          "GENERE par export_adkar.py depuis adkar_source.py.",
          "Ne pas editer a la main : les corrections vont dans adkar_source.py.",
          '"""',
          "",
          "HAUTEUR = %d" % HAUTEUR,
          "",
          "# (motif arabe, translitteration, sens court, signification)",
          "ENTREES = ("]
    for motif, latin, sens, detail in rendus:
        py.append("    (")
        py.append("        (")
        for ligne in motif:
            py.append('            "%s",' % ligne)
        py.append("        ),")
        py.append('        "%s",' % latin)
        py.append('        "%s",' % sens)
        py.append('        "%s",' % detail)
        py.append("    ),")
    py.append(")")
    py.append("")
    py.append("")
    py.append("def combien():")
    py.append('    """Nombre de noms disponibles."""')
    py.append("    return len(ENTREES)")
    py.append("")
    py.append("")
    py.append("def entree(rang):")
    py.append('    """Nom numero rang, en bouclant sur la liste."""')
    py.append("    if not ENTREES:")
    py.append("        return None")
    py.append("    return ENTREES[rang % len(ENTREES)]")
    py.append("")
    py.append("")
    py.append("def largeur(motif):")
    py.append('    """Largeur en pixels d\'un motif arabe."""')
    py.append("    return len(motif[0]) if motif else 0")
    py.append("")
    with open(os.path.join(HERE, "adkar.py"), "w", encoding="ascii") as handle:
        handle.write("\n".join(py))

    c = ["// adkar.h - les 99 noms d'Allah, en silhouettes",
         "//",
         "// GENERE par export_adkar.py depuis adkar_source.py.",
         "// Ne pas editer a la main.",
         "//",
         "// Jumeau d'adkar.py. Inclus depuis panneau_vols.ino AVANT",
         "// ecran_adkar.h.",
         "",
         "#ifndef ADKAR_H",
         "#define ADKAR_H",
         "",
         "static const int16_t ADKAR_H_PX = %d;" % HAUTEUR,
         ""]
    for n, (motif, latin, sens, detail) in enumerate(rendus):
        c.append("static const char *ADKAR_M%d[ADKAR_H_PX] = {" % n)
        for ligne in motif:
            c.append('    "%s",' % ligne)
        c.append("};")
    c.append("")
    c.append("struct Adkar { const char **motif; int16_t largeur;"
             " const char *latin; const char *sens; const char *detail; };")
    c.append("")
    c.append("static const Adkar ADKAR[] = {")
    for n, (motif, latin, sens, detail) in enumerate(rendus):
        c.append('    {ADKAR_M%d, %d, "%s", "%s",' % (n, len(motif[0]), latin,
                                                      sens))
        c.append('     "%s"},' % detail)
    c.append("};")
    c.append("static const int16_t ADKAR_COUNT = %d;" % len(rendus))
    c.append("")
    c.append("// Nom numero rang, en bouclant sur la liste.")
    c.append("static const Adkar *adkarEntree(int16_t rang) {")
    c.append("  if (ADKAR_COUNT <= 0) return nullptr;")
    c.append("  return &ADKAR[((rang % ADKAR_COUNT) + ADKAR_COUNT)"
             " % ADKAR_COUNT];")
    c.append("}")
    c.append("")
    c.append("#endif  // ADKAR_H")
    c.append("")
    with open(os.path.join(HERE, "firmware", "adkar.h"), "w",
              encoding="ascii") as handle:
        handle.write("\n".join(c))

    octets = sum((len(m[0]) + 1) * HAUTEUR for m, _, _, _ in rendus)
    octets += sum(len(l) + len(s) + len(d) + 3
                  for _, l, s, d in rendus)
    plus_large = max(len(m[0]) for m, _, _, _ in rendus)
    plus_long = max(len(d) for _, _, _, d in rendus)
    print("  %d noms" % len(rendus))
    print("  silhouette la plus large : %d px" % plus_large)
    print("  signification la plus longue : %d caracteres" % plus_long)
    print("  ~%d Ko de flash" % (octets // 1024))
    print("\nadkar.py et firmware/adkar.h ecrits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
