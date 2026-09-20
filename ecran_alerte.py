"""Ecrans d'annonce : ce qui arrive est annonce avant d'etre detaille.

Arrivee d'un avion, quand l'indicatif change :

    ~~~~>                                    silhouette, de droite a gauche
    AVION AU DESSUS                          annonce, centree
    AFR1234                                  indicatif du vol, centre

Heure d'une priere, quand elle prend la main :

        [^]                                  mosquee, glisse et se pose
    C'EST L'HEURE                            annonce, centree
    MAGHREB                                  nom de la priere, centre

L'avion traverse, la mosquee se pose : un avion passe au-dessus, une mosquee
non. Les deux durent ALERTE_MS, puis le panneau bascule sur les details par la
transition habituelle.

Cette detection est faite des deux cotes du jumeau, avec la meme regle et la
meme duree, et non arbitree par la passerelle comme l'est la rotation :
l'ESP32 n'interroge la passerelle que toutes les trois secondes et pourrait
manquer une fenetre de deux secondes.

Jumeau de firmware/ecran_alerte.h.
"""

import cadre
import panel
import transitions
from panel import ACCENT, LINE2_Y, LINE3_Y, PRINCIPAL, TEXTE, WIDTH

# Mise en page - memes valeurs dans firmware/ecran_alerte.h
ALERTE_MS = 2200
AVION_Y = 1          # bande du haut, la silhouette fait 9 pixels de haut
MOSQUEE_Y = 1
ANNONCE = "AVION AU DESSUS"
ANNONCE_PRIERE = "C'EST L'HEURE"

# Silhouette vue de dessus, nez a gauche, ailes en fleche. Meme motif que du
# cote C : la bande du haut va de AVION_Y a LINE2_Y, soit dix pixels.
AVION = (
    "..............#..",
    ".....#.......##..",
    "....##......###..",
    "...###.....####..",
    ".################",
    "...###.....####..",
    "....##......###..",
    ".....#.......##..",
    "..............#..",
)
AVION_W = len(AVION[0])
AVION_H = len(AVION)

# Mosquee : coupole, fleche et minaret. Meme motif que du cote C.
MOSQUEE = (
    "..............#..",
    ".......#.....###.",
    "......###....###.",
    ".....#####...###.",
    "....#######..###.",
    "...#########.###.",
    "...#########.###.",
    "...#########.###.",
    ".################",
)
MOSQUEE_W = len(MOSQUEE[0])
MOSQUEE_H = len(MOSQUEE)


def _centre(frame, y, texte, couleur):
    cadre.centre(frame, y, texte, couleur)


def position_avion(avancement):
    """Abscisse de la silhouette, de la droite du cadre jusqu'au dela du bord.

    Lineaire : un avion garde sa vitesse, l'adoucissement des transitions
    n'aurait pas de sens ici.
    """
    depart = WIDTH
    arrivee = -AVION_W
    return int(round(depart + (arrivee - depart) * min(1.0, max(0.0, avancement))))


def position_mosquee(avancement):
    """Abscisse de la mosquee : elle entre par la droite et se pose au centre.

    Adoucie, contrairement a l'avion : celui-ci traverse a vitesse constante,
    celle-la arrive et s'arrete, donc elle freine.
    """
    depart = WIDTH
    arrivee = (WIDTH - MOSQUEE_W) // 2
    return int(round(depart + (arrivee - depart) * transitions.adoucis(avancement)))


def render(flight, avancement=0.0, frame=None):
    """Compose l'ecran d'annonce d'un avion.

    avancement : 0.0 au debut de l'alerte, 1.0 a la fin.
    frame : cadre existant ou dessiner sans effacer (cf. transitions.py).
    """
    if frame is None:
        frame = panel.Frame()
    frame.draw_sprite(position_avion(avancement), AVION_Y, AVION, TEXTE)
    _centre(frame, LINE2_Y, ANNONCE, PRINCIPAL)
    _centre(frame, LINE3_Y, (flight or {}).get("callsign") or "", ACCENT)
    return frame


def render_priere(info, avancement=0.0, frame=None):
    """Compose l'ecran d'annonce d'une priere."""
    if frame is None:
        frame = panel.Frame()
    frame.draw_sprite(position_mosquee(avancement), MOSQUEE_Y, MOSQUEE, TEXTE)
    _centre(frame, LINE2_Y, ANNONCE_PRIERE, PRINCIPAL)
    _centre(frame, LINE3_Y, (info or {}).get("nom") or "", ACCENT)
    return frame
