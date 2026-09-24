"""Convertit logos/*.png en firmware/logos.h, lisible par l'ESP32.

    python3 export_logos.py [dossier]

L'ESP32 ne sait pas decoder du PNG : les images sont donc converties ici en
RGB565 et posees dans un en-tete C. Elles y sont declarees const, donc rangees
en flash et non en SRAM - c'est ce qui permet d'en embarquer plusieurs dizaines
sans toucher aux 276 Ko de SRAM libre. Compter 1152 octets de flash par logo,
verifie a la compilation : 60 logos pesent 69 976 octets.

Le fichier genere n'est pas versionne : les logos de compagnies sont des
marques deposees (voir logos/LISEZMOI.txt).

Pillow est necessaire pour ce script, et pour lui seul.
"""

import os
import sys

import panel

TAILLE = panel.LOGO_PX
SORTIE = os.path.join("firmware", "logos.h")

# Garde-fou de bon sens, et limite verifiee : avec le schema de partition
# OTA (Minimal SPIFFS, 1,9 Mo par emplacement), le croquis plus ce budget
# plein (177 logos) occupe 70 % d'un emplacement, compile en CI avec des
# logos factices. Le depot source des logos en compte pres d'un millier :
# tout prendre ne tiendrait pas, pour des compagnies qui ne passeront jamais
# au-dessus de la maison.
BUDGET_FLASH = 200 * 1024


def rgb565(couleur):
    """(r, g, b) sur 8 bits -> couleur 16 bits 5-6-5.

    Le vert garde un bit de plus que le rouge et le bleu, c'est la convention
    RGB565 : l'oeil y est plus sensible.
    """
    r, v, b = couleur[0], couleur[1], couleur[2]
    return ((r & 0xF8) << 8) | ((v & 0xFC) << 3) | (b >> 3)


def _charge(icao, dossier):
    """PNG -> liste de TAILLE*TAILLE couleurs 16 bits, ou None.

    Le chargement et la mise a l'echelle sont ceux du simulateur, via
    panel._load_logo : les deux moities du jumeau doivent partir de la meme
    image, sinon le panneau et l'ecran ne montrent pas la meme chose. Ne pas
    reecrire un redimensionnement ici.

    Les pixels noirs ne sont pas dessines par le firmware, ce qui donne le
    fond transparent.
    """
    bitmap = panel._load_logo(icao, dossier)
    if bitmap is None:
        return None
    return [rgb565(couleur) for couleur in bitmap[2]]


def _entete(logos):
    lignes = [
        "// logos.h - logos des compagnies en RGB565, genere par export_logos.py",
        "//",
        "// NE PAS EDITER A LA MAIN. Relancer :  python3 export_logos.py",
        "//",
        "// Marques deposees : fichier non versionne, usage personnel.",
        "",
        "#ifndef LOGOS_H",
        "#define LOGOS_H",
        "",
        "static const int16_t LOGO_W = %d;" % TAILLE,
        "static const int16_t LOGO_H = %d;" % TAILLE,
        "",
    ]

    for icao, pixels in logos:
        lignes.append("static const uint16_t LOGO_%s[] = {" % icao)
        for debut in range(0, len(pixels), 12):
            tranche = pixels[debut:debut + 12]
            lignes.append("  " + " ".join("0x%04X," % p for p in tranche))
        lignes.append("};")
        lignes.append("")

    lignes.append("struct LogoEntry { const char *icao; const uint16_t *pixels; };")
    lignes.append("")
    lignes.append("static const LogoEntry LOGOS[] = {")
    for icao, _ in logos:
        lignes.append('  {"%s", LOGO_%s},' % (icao, icao))
    lignes.append("};")
    lignes.append("static const size_t LOGO_COUNT = %d;" % len(logos))
    lignes.append("")
    lignes.append("// Renvoie le logo d'une compagnie, ou nullptr si inconnue.")
    lignes.append("static const uint16_t *logoFor(const char *icao) {")
    lignes.append("  if (!icao || !icao[0]) return nullptr;")
    lignes.append("  for (size_t i = 0; i < LOGO_COUNT; i++)")
    lignes.append("    if (strcmp(LOGOS[i].icao, icao) == 0) return LOGOS[i].pixels;")
    lignes.append("  return nullptr;")
    lignes.append("}")
    lignes.append("")
    lignes.append("#endif  // LOGOS_H")
    lignes.append("")
    return "\n".join(lignes)


def main():
    dossier = sys.argv[1] if len(sys.argv) > 1 else "logos"
    here = os.path.dirname(os.path.abspath(__file__))
    dossier = dossier if os.path.isabs(dossier) else os.path.join(here, dossier)

    if not os.path.isdir(dossier):
        print("dossier introuvable :", dossier)
        return 1

    noms = sorted(n for n in os.listdir(dossier) if n.lower().endswith(".png"))
    if not noms:
        print("aucun PNG dans %s." % dossier)
        print("Deposez-y les logos nommes par code OACI : AFR.png, EZY.png...")
        return 1

    logos = []
    for nom in noms:
        icao = os.path.splitext(nom)[0].upper()
        if not icao.isalnum():
            print("ignore (nom non alphanumerique) :", nom)
            continue
        pixels = _charge(icao, dossier)
        if pixels is None:
            print("%-6s illisible, ignore" % icao)
            continue
        logos.append((icao, pixels))

    if not logos:
        print("aucun logo exploitable.")
        return 1

    octets = len(logos) * TAILLE * TAILLE * 2
    if octets > BUDGET_FLASH:
        print("STOP : %d logos font %d Ko de flash, au-dela des %d Ko prudents."
              % (len(logos), octets // 1024, BUDGET_FLASH // 1024))
        print("Retirez des PNG de %s, ou relevez BUDGET_FLASH en connaissance"
              " de cause." % dossier)
        return 1

    chemin = os.path.join(here, SORTIE)
    with open(chemin, "w", encoding="ascii") as handle:
        handle.write(_entete(logos))

    print("%d logos : %s" % (len(logos), " ".join(i for i, _ in logos)))
    print("\n%s ecrit : %d octets de flash (budget %d Ko)"
          % (SORTIE, octets, BUDGET_FLASH // 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
