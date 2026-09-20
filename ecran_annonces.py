"""Ecran des annonces de la mosquee, en bandeau defilant.

    MOSQUEE                     23:07     en-tete, mosquee et heure
    CONFERENCE VENDREDI 20H * COURS...   bandeau defilant

Meme langage visuel que l'ecran des horaires : en-tete discret, bandeau a
l'echelle 2 en dessous. Ce sont les deux seuls ecrans qui ont quelque chose
d'assez long a dire pour meriter un defilement.

Le texte vient de la mosquee, via annonces.py qui l'a deja nettoye : ici on
ne fait que le mettre en page.

Jumeau de firmware/ecran_annonces.h.
"""

import cadre
import panel
from panel import PRINCIPAL, SECONDAIRE, WIDTH

# Mise en page - memes valeurs dans firmware/ecran_annonces.h
ANNONCES_X0 = 2
ANNONCES_X1 = WIDTH - 3
ANNONCES_BANDE_Y = 13
ANNONCES_ECHELLE = 2
ANNONCES_ENTRE = 18         # vide entre deux annonces, separateur compris
ANNONCES_PX_PAR_SEC = 22.0  # meme cadence que le bandeau des horaires
SEPARATEUR = "*"
TITRE = "ANNONCES"


def largeur_bandeau(titres):
    """Largeur d'un tour complet du bandeau, en pixels."""
    if not titres:
        return 0
    return sum(cadre.largeur_echelle(t, ANNONCES_ECHELLE) + ANNONCES_ENTRE
               + cadre.largeur_echelle(SEPARATEUR, ANNONCES_ECHELLE)
               + ANNONCES_ENTRE for t in titres)


def duree_tour(titres):
    """Secondes que met le bandeau a faire un tour complet."""
    large = largeur_bandeau(titres)
    return large / ANNONCES_PX_PAR_SEC if large else 0.0


def _bloc(frame, x, titre, clip):
    """Une annonce et son separateur ; renvoie la largeur consommee."""
    frame.draw_text_echelle(x, ANNONCES_BANDE_Y, titre, PRINCIPAL,
                            ANNONCES_ECHELLE, clip)
    x += cadre.largeur_echelle(titre, ANNONCES_ECHELLE) + ANNONCES_ENTRE
    frame.draw_text_echelle(x, ANNONCES_BANDE_Y, SEPARATEUR, SECONDAIRE,
                            ANNONCES_ECHELLE, clip)
    return (cadre.largeur_echelle(titre, ANNONCES_ECHELLE) + ANNONCES_ENTRE
            + cadre.largeur_echelle(SEPARATEUR, ANNONCES_ECHELLE)
            + ANNONCES_ENTRE)


def render(info, elapsed=0.0, frame=None):
    """Compose l'ecran des annonces.

    info : dict de prieresource.poll(), pour la mosquee, l'heure et la liste
    des annonces. None ou liste vide affiche l'ecran de veille.
    """
    titres = (info or {}).get("annonces") or ()
    if not titres:
        return panel.render(None, frame=frame,
                            heure=(info or {}).get("heure"))

    if frame is None:
        frame = panel.Frame()
    clip = (ANNONCES_X0, ANNONCES_X1)

    # En-tete : la mosquee a gauche, l'heure a droite. Le panneau reste une
    # horloge murale, quel que soit l'ecran.
    frame.draw_text(ANNONCES_X0, panel.LINE1_Y, info.get("mosquee") or TITRE,
                    SECONDAIRE, clip)
    cadre.droite(frame, ANNONCES_X1, panel.LINE1_Y, info.get("heure") or "",
                 SECONDAIRE, clip)

    span = largeur_bandeau(titres)
    if span <= 0:
        return frame
    avance = int(elapsed * ANNONCES_PX_PAR_SEC) % span
    depart = ANNONCES_X0 - avance

    # Deux passages : le second bouche le trou pendant que le premier sort
    for repetition in range(2):
        x = depart + repetition * span
        if x > ANNONCES_X1:
            break
        for titre in titres:
            large = (cadre.largeur_echelle(titre, ANNONCES_ECHELLE)
                     + ANNONCES_ENTRE
                     + cadre.largeur_echelle(SEPARATEUR, ANNONCES_ECHELLE)
                     + ANNONCES_ENTRE)
            if x + large > ANNONCES_X0:
                _bloc(frame, x, titre, clip)
            x += large
    return frame
