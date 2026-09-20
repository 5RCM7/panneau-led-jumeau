"""Ecran meteo : temps qu'il fait au-dessus de la maison.

    [icone]  18 C            icone, temperature, ressenti a droite
    COUVERT                  temps qu'il fait
    PARIS        4 KM/H    lieu et vent

La troisieme ligne cede la place a l'averse qui approche quand il y en a
une : le lieu, on le connait, l'averse non.

Jumeau de firmware/ecran_meteo.h.
"""

import cadre
import font5x7
import icones_meteo
import panel
import transitions
from panel import (ACCENT, LINE1_Y, LINE2_Y, LINE3_Y, PRINCIPAL, SECONDAIRE,
                   TEXTE)

# Mise en page - memes valeurs dans firmware/ecran_meteo.h
METEO_X0 = 2
METEO_X1 = panel.WIDTH - 3
METEO_ICONE_Y = 1
METEO_TEXTE_X = 24  # a droite de l'icone, qui fait 17 pixels de large
ANNONCE_METEO = "METEO"
ANNONCE_PLUIE = "PLUIE DANS"
PLUIE_BIENTOT_MIN = 60  # en deca on compte en minutes, au-dela on donne l'heure


def temperature(valeur):
    """-3 -> '-3 C' avec le glyphe degre. Chaine vide si la valeur manque."""
    if valeur is None:
        return ""
    return "%d%sC" % (valeur, font5x7.DEGRE)


def texte_pluie(meteo):
    """Alerte pluie de la ligne du bas, ou chaine vide s'il n'en vient pas.

    Sous l'heure qui vient, un decompte parle mieux : on decide de sortir ou
    d'attendre. Plus loin, l'heure de debut se retient mieux qu'un nombre de
    minutes qu'il faudrait convertir.
    """
    minutes = (meteo or {}).get("pluie_min")
    if minutes is None:
        return ""
    if minutes < PLUIE_BIENTOT_MIN:
        return "PLUIE %d MIN" % minutes
    heure = (meteo.get("pluie_heure") or "").strip()
    return "PLUIE %s" % heure if heure else "PLUIE %d MIN" % minutes


def annonce_pluie(meteo):
    """Ligne d'annonce quand une averse approche, ou chaine vide."""
    minutes = (meteo or {}).get("pluie_min")
    if minutes is None:
        return ""
    return "%s %d MIN" % (ANNONCE_PLUIE, minutes)


def render(meteo, frame=None):
    """Compose l'ecran meteo.

    meteo : dict de meteosource.poll(), ou None si la meteo est indisponible.
    """
    if not meteo:
        return panel.render(None, frame=frame)

    if frame is None:
        frame = panel.Frame()
    clip = (METEO_X0, METEO_X1)

    frame.draw_sprite(METEO_X0, METEO_ICONE_Y,
                      icones_meteo.icone(meteo.get("icone")), TEXTE)

    # Ligne 1 : temperature a cote de l'icone, ressenti cale a droite
    frame.draw_text(METEO_TEXTE_X, LINE1_Y,
                    temperature(meteo.get("temperature")), PRINCIPAL, clip)
    ressenti = meteo.get("ressenti")
    if ressenti is not None and ressenti != meteo.get("temperature"):
        cadre.droite(frame, METEO_X1, LINE1_Y, "~" + temperature(ressenti),
                     SECONDAIRE, clip)

    # Ligne 2 : le temps qu'il fait a gauche, l'heure a droite
    frame.draw_text(METEO_X0, LINE2_Y, meteo.get("texte") or "", ACCENT, clip)
    cadre.droite(frame, METEO_X1, LINE2_Y, meteo.get("heure") or "",
                 SECONDAIRE, clip)

    # Ligne 3 : lieu a gauche, vent a droite - sauf si une averse arrive,
    # auquel cas elle prend la place du lieu et passe en orange
    pluie = texte_pluie(meteo)
    if pluie:
        frame.draw_text(METEO_X0, LINE3_Y, pluie, TEXTE, clip)
    else:
        frame.draw_text(METEO_X0, LINE3_Y, meteo.get("lieu") or "",
                        SECONDAIRE, clip)
    vent = meteo.get("vent_kmh")
    if vent is not None:
        cadre.droite(frame, METEO_X1, LINE3_Y, "%d KM/H" % vent, TEXTE, clip)

    return frame


def position_icone(avancement):
    """Abscisse de l'icone pendant l'annonce : elle entre et se pose au centre.

    Meme mouvement que la mosquee, et pour la meme raison : le temps qu'il
    fait ne traverse pas le ciel, il s'installe.
    """
    arrivee = (panel.WIDTH - icones_meteo.LARGEUR) // 2
    return int(round(panel.WIDTH
                     + (arrivee - panel.WIDTH) * transitions.adoucis(avancement)))


def render_annonce(meteo, avancement=0.0, frame=None):
    """Annonce de la meteo, sur le modele des autres annonces.

        [icone]                 icone qui entre et se pose
        METEO PARIS           annonce, centree
        18 C  COUVERT           temperature et temps, centres
    """
    if not meteo:
        return panel.render(None, frame=frame)

    if frame is None:
        frame = panel.Frame()

    frame.draw_sprite(position_icone(avancement), METEO_ICONE_Y,
                      icones_meteo.icone(meteo.get("icone")), TEXTE)

    # L'averse qui approche vaut mieux qu'un rappel du nom de la commune
    annonce = annonce_pluie(meteo)
    if not annonce:
        annonce = (ANNONCE_METEO + " " + (meteo.get("lieu") or "")).strip()
    cadre.centre(frame, LINE2_Y, annonce, PRINCIPAL)

    valeur = temperature(meteo.get("temperature"))
    texte = meteo.get("texte") or ""
    cadre.centre(frame, LINE3_Y, ("%s  %s" % (valeur, texte)).strip(), ACCENT)
    return frame
