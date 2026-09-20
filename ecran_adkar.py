"""Ecran adkar : un nom d'Allah par jour, sa signification en defilement.

    ADKAR 12/99                 23:07     en-tete, rang du jour et heure
            [arabe]                       le nom, centre
    AL-AZIZ - LE TOUT PUISSANT - PUIS...  sens et signification, defilants

Un nom par jour, et non un qui tourne a la minute : on a le temps de le
retenir, et le panneau ne ressemble pas a un bandeau publicitaire. Le rang
vient de la passerelle, qui le tire de la date.

La ligne du bas porte la translitteration, le sens court et la signification
detaillee. Elle depasse toujours les 128 pixels, donc elle defile ; un tour
complet tient dans la duree de l'ecran, un test le verifie.

Jumeau de firmware/ecran_adkar.h.
"""

import adkar
import cadre
import font5x7
import panel
from panel import ACCENT, PRINCIPAL, SECONDAIRE, WIDTH

# Mise en page - memes valeurs dans firmware/ecran_adkar.h
ADKAR_X0 = 2
ADKAR_X1 = WIDTH - 3
ADKAR_ENTETE_Y = 0
ADKAR_MOT_Y = 9
ADKAR_SENS_Y = 25
ADKAR_PX_PAR_SEC = 20.0     # defilement de la ligne du bas
ADKAR_GAP = 14              # vide entre deux passages du texte defilant
TITRE = "ADKAR"


def entete(rang):
    """En-tete de gauche : le titre, et ou l'on en est dans les 99."""
    combien = adkar.combien()
    if not combien:
        return TITRE
    return "%s %d/%d" % (TITRE, rang % combien + 1, combien)


def texte_bas(entree):
    """Ligne defilante : translitteration, sens court, puis signification."""
    return " - ".join(m for m in entree[1:] if m)


def duree_defilement(entree):
    """Secondes que met la ligne du bas a faire un tour complet.

    La passerelle s'en sert pour verifier que l'ecran reste assez longtemps a
    l'antenne : une signification coupee en deux ne servirait a personne.
    """
    span = font5x7.text_width(texte_bas(entree)) + ADKAR_GAP
    return span / ADKAR_PX_PAR_SEC


def render(rang, elapsed=0.0, heure=None, frame=None):
    """Compose l'ecran adkar.

    rang : numero du nom du jour, tel que le donne la passerelle. None
    affiche l'ecran de veille.
    elapsed : secondes ecoulees, pilote le defilement de la ligne du bas.
    """
    entree = adkar.entree(rang) if rang is not None else None
    if not entree:
        return panel.render(None, frame=frame, heure=heure)

    if frame is None:
        frame = panel.Frame()
    clip = (ADKAR_X0, ADKAR_X1)
    motif = entree[0]

    # En-tete : le titre et le rang a gauche, l'heure a droite. Le panneau
    # reste une horloge murale, quel que soit l'ecran.
    frame.draw_text(ADKAR_X0, ADKAR_ENTETE_Y, entete(rang), SECONDAIRE, clip)
    cadre.droite(frame, ADKAR_X1, ADKAR_ENTETE_Y, heure or "", SECONDAIRE,
                 clip)

    # Le nom en arabe, centre
    large = adkar.largeur(motif)
    frame.draw_sprite((WIDTH - large) // 2, ADKAR_MOT_Y, motif, PRINCIPAL,
                      clip)

    # Sens et signification, defilants s'ils depassent la largeur
    bas = texte_bas(entree)
    largeur_bas = font5x7.text_width(bas)
    if largeur_bas <= ADKAR_X1 - ADKAR_X0 + 1:
        x = (WIDTH - largeur_bas) // 2
        frame.draw_text(x, ADKAR_SENS_Y, bas, ACCENT, clip)
    else:
        span = largeur_bas + ADKAR_GAP
        offset = int(elapsed * ADKAR_PX_PAR_SEC) % span
        frame.draw_text(ADKAR_X0 - offset, ADKAR_SENS_Y, bas, ACCENT, clip)
        frame.draw_text(ADKAR_X0 - offset + span, ADKAR_SENS_Y, bas, ACCENT,
                        clip)
    return frame
