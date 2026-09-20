"""Horaires de priere en bandeau defilant, arabe et francais.

    MOSQUEE                             23:07   en-tete, mosquee et heure
    [arabe] FAJR 05:55  [arabe] DOHR 13:45 ...  bande defilante

Le bandeau enchaine les cinq prieres du jour, chacune annoncee en arabe puis
en francais, comme le bandeau d'une chaine d'info. La priere a venir est mise
en valeur.

L'arabe ne peut pas sortir de la police 5x7, qui est ASCII pure : ce sont des
silhouettes generees par export_arabe.py, dans arabe.py et firmware/arabe.h.

Jumeau de firmware/ecran_horaires.h.
"""

import arabe
import cadre
import font5x7
import panel
from panel import (ACCENT, LINE1_Y, PRINCIPAL, SECONDAIRE, TEXTE, WIDTH)

# Mise en page - memes valeurs dans firmware/ecran_horaires.h
HORAIRES_X0 = 2
HORAIRES_X1 = WIDTH - 3
HORAIRES_BANDE_Y = 13       # haut de la silhouette arabe
HORAIRES_LATIN_DY = 1       # le latin fait 14 px, l'arabe 16 : on le recentre
HORAIRES_ECHELLE = 2        # un glyphe de 5x7 devient 10x14
HORAIRES_GAP = 4            # entre l'arabe et le latin
HORAIRES_ENTRE = 14         # entre deux prieres
HORAIRES_PX_PAR_SEC = 22.0  # lecture confortable a distance, sur un mur

# Abreges a trois lettres, dans l'ordre de horaires.NOMS. Le vendredi, la
# priere de midi devient la Joumoua.
ABREGES = ("FAJ", "DOH", "ASR", "MAG", "ICH")
ABREGE_JOUMOUA = "JOU"


def abrege(nom, rang):
    """Nom court d'une priere, a partir de son nom complet et de son rang."""
    if nom and nom.startswith("JOU"):
        return ABREGE_JOUMOUA
    return ABREGES[rang] if 0 <= rang < len(ABREGES) else (nom or "")[:3]


def _latin(nom, heure):
    """Texte latin d'un bloc : 'FAJR 05:55'."""
    return ("%s %s" % (nom or "", heure or "")).strip()


def largeur_bloc(nom, heure):
    """Largeur d'une priere dans le bandeau, separateur compris."""
    large = arabe.largeur(nom)
    if large:
        large += HORAIRES_GAP
    return large + cadre.largeur_echelle(_latin(nom, heure),
                                         HORAIRES_ECHELLE) + HORAIRES_ENTRE


def largeur_bandeau(jour):
    """Largeur totale du bandeau, pour savoir quand il se repete."""
    return sum(largeur_bloc(p.get("nom"), p.get("adhan")) for p in jour[:5])


def _dessine_bloc(frame, x, nom, heure, courante):
    """Un couple arabe + latin, et la largeur consommee."""
    couleur_nom = PRINCIPAL if courante else SECONDAIRE
    couleur_heure = ACCENT if courante else TEXTE
    clip = (HORAIRES_X0, HORAIRES_X1)

    motif = arabe.mot(nom)
    if motif:
        frame.draw_sprite(x, HORAIRES_BANDE_Y, motif, couleur_nom, clip)
        x += arabe.largeur(nom) + HORAIRES_GAP

    y = HORAIRES_BANDE_Y + HORAIRES_LATIN_DY
    court = (nom or "")[:7]
    frame.draw_text_echelle(x, y, court, couleur_nom, HORAIRES_ECHELLE, clip)
    x += cadre.largeur_echelle(court, HORAIRES_ECHELLE)
    x += font5x7.ADVANCE * HORAIRES_ECHELLE  # l'espace avant l'heure
    frame.draw_text_echelle(x, y, heure or "", couleur_heure,
                            HORAIRES_ECHELLE, clip)


def render(info, elapsed=0.0, frame=None):
    """Compose le bandeau des horaires.

    info : dict de horaires.next_prayer(), qui porte la journee sous 'jour'
    et le rang de la priere a venir sous 'rang'.
    elapsed : secondes ecoulees, pilote le defilement.
    """
    jour = (info or {}).get("jour") or []
    if not jour:
        return panel.render(None, frame=frame)

    if frame is None:
        frame = panel.Frame()

    # En-tete : mosquee a gauche, heure a droite. Le panneau reste une
    # horloge murale, meme quand le bandeau occupe le reste de la hauteur.
    clip = (HORAIRES_X0, HORAIRES_X1)
    frame.draw_text(HORAIRES_X0, LINE1_Y, (info or {}).get("mosquee") or "",
                    SECONDAIRE, clip)
    cadre.droite(frame, HORAIRES_X1, LINE1_Y, (info or {}).get("heure") or "",
                 SECONDAIRE, clip)

    rang_courant = (info or {}).get("rang", -1)
    span = largeur_bandeau(jour) or 1
    depart = HORAIRES_X0 - int(elapsed * HORAIRES_PX_PAR_SEC) % span

    # Deux passages : le second bouche le trou pendant que le premier sort
    for repetition in (0, 1):
        x = depart + repetition * span
        if x > HORAIRES_X1:
            break
        for rang, priere in enumerate(jour[:5]):
            nom = priere.get("nom") or ""
            heure = priere.get("adhan") or ""
            if x + largeur_bloc(nom, heure) > HORAIRES_X0:
                _dessine_bloc(frame, x, nom, heure, rang == rang_courant)
            x += largeur_bloc(nom, heure)
    return frame
