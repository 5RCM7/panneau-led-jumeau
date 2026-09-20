"""Transition entre deux ecrans du panneau : un roulement vertical.

L'ecran sortant monte, l'entrant le suit par le bas, comme une pancarte qui
tourne dans un tableau de gare. Aucun tampon supplementaire n'est necessaire :
on dessine les deux ecrans dans la meme image, decales par Frame.dy, et ce qui
deborde est perdu.

Jumeau de firmware/transitions.h. La duree et la courbe doivent rester
identiques des deux cotes, sinon les deux panneaux n'animent pas pareil.
"""

import panel

# Mise en page - memes valeurs dans firmware/transitions.h
TRANSITION_MS = 450


def adoucis(avancement):
    """Courbe en S : demarrage et arrivee freines, milieu rapide.

    Meme formule que du cote C. Une transition lineaire donne un a-coup net
    en debut et en fin de course, tres visible sur 32 pixels de haut.
    """
    t = min(1.0, max(0.0, avancement))
    return t * t * (3.0 - 2.0 * t)


def compose(sortant, entrant, avancement):
    """Image intermediaire entre deux ecrans.

    sortant, entrant : fonctions prenant un Frame et y dessinant un ecran.
    avancement : 0.0 au debut de la transition, 1.0 a la fin.
    """
    frame = panel.Frame()
    decalage = int(round(adoucis(avancement) * panel.HEIGHT))

    frame.dy = -decalage
    sortant(frame)
    frame.dy = panel.HEIGHT - decalage
    entrant(frame)
    frame.dy = 0
    return frame


def en_cours(depuis_ms):
    """Vrai tant que la transition n'est pas terminee."""
    return 0 <= depuis_ms < TRANSITION_MS


def avancement(depuis_ms):
    """Position dans la transition, entre 0.0 et 1.0."""
    if depuis_ms <= 0:
        return 0.0
    return min(1.0, depuis_ms / float(TRANSITION_MS))
