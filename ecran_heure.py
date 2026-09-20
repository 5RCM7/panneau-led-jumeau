"""Ecran de l'heure : rien d'autre, en gros.

         22:33            heure a l'echelle 3, centree
     VENDREDI 19 SEPT     date du jour, centree

L'heure vient de la passerelle et non de l'ESP32, qui n'a ni horloge
sauvegardee ni client NTP : c'est le meme choix que pour l'ecran des prieres.

Jumeau de firmware/ecran_heure.h.
"""

import cadre
import panel
from panel import PRINCIPAL, SECONDAIRE

# Mise en page - memes valeurs dans firmware/ecran_heure.h
HEURE_ECHELLE = 3   # un glyphe de 5x7 devient 15x21
HEURE_Y = 1
DATE_Y = 24

# Sans accents, la police n'en a pas. Index 0 = lundi, comme weekday().
JOURS = ("LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI",
         "DIMANCHE")
MOIS = ("JANV", "FEVR", "MARS", "AVRIL", "MAI", "JUIN", "JUIL", "AOUT",
        "SEPT", "OCT", "NOV", "DEC")


def format_date(quand):
    """datetime -> 'VENDREDI 19 SEPT', qui tient sur la largeur du panneau."""
    return "%s %d %s" % (JOURS[quand.weekday()], quand.day,
                         MOIS[quand.month - 1])


def render(info, frame=None):
    """Compose l'ecran de l'heure.

    info : dict {heure, date}, ou None si la passerelle n'a rien envoye.
    """
    heure = (info or {}).get("heure") or ""
    if not heure:
        return panel.render(None, frame=frame)

    if frame is None:
        frame = panel.Frame()

    cadre.centre_echelle(frame, HEURE_Y, heure, PRINCIPAL, HEURE_ECHELLE)
    cadre.centre(frame, DATE_Y, (info or {}).get("date") or "", SECONDAIRE)
    return frame
