"""Ecran de liaison perdue : quand la passerelle ne repond plus.

        LIAISON PERDUE           ce qui se passe
       HEURE NON FIABLE          ce que ca change
         DEPUIS 4 MIN            depuis quand

Le panneau n'a ni horloge sauvegardee ni client NTP : l'heure lui vient de
la passerelle, comme le reste. Passerelle muette, heure figee - et une
horloge murale qui affiche avec aplomb l'heure d'il y a vingt minutes est
pire qu'un ecran noir, parce qu'on la croit.

D'ou cet ecran plutot qu'un discret temoin dans un coin : il ne s'agit pas
de signaler un detail, mais de retirer sa confiance a tout ce qui est
affiche. Il prend la main sur la rotation, annonces comprises.

Le delai de grace evite qu'une coupure Wi-Fi de quelques secondes ne fasse
clignoter le salon.

Jumeau de firmware/ecran_liaison.h.
"""

import cadre
import panel
from panel import LINE1_Y, LINE2_Y, LINE3_Y, PRINCIPAL, SECONDAIRE, TEXTE

# Mise en page et tempo - memes valeurs dans firmware/ecran_liaison.h
LIAISON_SEUIL_MS = 90000    # trois polls manques d'affilee, et de la marge
TITRE = "LIAISON PERDUE"
SOUS_TITRE = "HEURE NON FIABLE"
DEPUIS = "DEPUIS"


def perdue(depuis_ms):
    """Vrai quand le silence a assez dure pour qu'on ne croie plus rien."""
    return depuis_ms is not None and depuis_ms >= LIAISON_SEUIL_MS


def format_depuis(depuis_ms):
    """Duree du silence, en trois mots au plus."""
    if depuis_ms is None:
        return ""
    minutes = int(depuis_ms // 60000)
    if minutes < 60:
        return "%s %d MIN" % (DEPUIS, minutes)
    return "%s %dH" % (DEPUIS, minutes // 60)


def render(depuis_ms=None, frame=None):
    """Compose l'ecran de liaison perdue."""
    if frame is None:
        frame = panel.Frame()
    cadre.centre(frame, LINE1_Y, TITRE, PRINCIPAL)
    cadre.centre(frame, LINE2_Y, SOUS_TITRE, TEXTE)
    texte = format_depuis(depuis_ms)
    if texte:
        cadre.centre(frame, LINE3_Y, texte, SECONDAIRE)
    return frame
