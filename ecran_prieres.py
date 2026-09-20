"""Ecran des horaires de priere, deuxieme mise en page du panneau.

Sur toute la largeur, sans zone logo, contrairement a l'ecran des vols :

    MOSQUEE                    21:04      en-tete, mosquee et heure
    ----------------------------------    filet de separation
    MAGHREB                    19:59      priere et heure de l'adhan
    IQAMA 20:09               12 MIN      iqama et temps restant

Comme panel.py, ce fichier a son jumeau dans le firmware :
firmware/ecran_prieres.h. Toute modification de la mise en page doit
etre reportee des deux cotes dans le meme commit.
"""

import cadre
import panel
from panel import (TEXTE, ACCENT, SECONDAIRE, LINE1_Y, LINE2_Y, LINE3_Y,
                   SEP, PRINCIPAL, WIDTH)

# Mise en page - memes valeurs dans firmware/ecran_prieres.h
PRIERE_X0 = 2
PRIERE_X1 = WIDTH - 3
PRIERE_RULE_Y = 9


def _droite(frame, y, texte, couleur):
    """Texte cale sur le bord droit de la zone."""
    cadre.droite(frame, PRIERE_X1, y, texte, couleur, (PRIERE_X0, PRIERE_X1))


def render(info, now=None, frame=None):
    """Compose l'ecran des prieres.

    info : dict renvoye par horaires.next_prayer(), ou None si les
    horaires sont indisponibles - on retombe alors sur l'ecran de veille.
    frame : cadre existant ou l'on dessine sans effacer (cf. transitions.py).
    """
    if not info:
        return panel.render(None, frame=frame)

    if frame is None:
        frame = panel.Frame()
    clip = (PRIERE_X0, PRIERE_X1)

    # En-tete : mosquee a gauche, heure courante a droite
    frame.draw_text(PRIERE_X0, LINE1_Y, info.get("mosquee") or "", SECONDAIRE, clip)
    heure = now or info.get("heure") or panel.flight_none_clock()
    _droite(frame, LINE1_Y, heure, SECONDAIRE)

    for x in range(PRIERE_X0, PRIERE_X1 + 1):
        frame.set(x, PRIERE_RULE_Y, SEP)

    # Priere en cours ou a venir : en blanc des que le panneau prend la main,
    # pour qu'on voie d'un coup d'oeil que c'est le moment de partir
    couleur_nom = PRINCIPAL if info.get("prise_main") else ACCENT
    nom = (info.get("nom") or "")[:9]
    if info.get("demain"):
        nom = nom + " +1"
    frame.draw_text(PRIERE_X0, LINE2_Y, nom, couleur_nom, clip)
    _droite(frame, LINE2_Y, info.get("adhan") or "", couleur_nom)

    # Bas : iqama a gauche, compte a rebours a droite
    iqama = info.get("iqama") or ""
    if iqama and iqama != info.get("adhan"):
        frame.draw_text(PRIERE_X0, LINE3_Y, "IQAMA " + iqama, TEXTE, clip)
    if info.get("phase") == "encours":
        _droite(frame, LINE3_Y, "EN COURS", PRINCIPAL)
    else:
        _droite(frame, LINE3_Y, info.get("restant") or "", TEXTE)

    return frame
