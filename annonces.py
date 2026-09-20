"""Annonces de la mosquee, tirees du confData deja en cache.

Mawaqit laisse la mosquee publier ses annonces ; elles voyagent dans le meme
confData que les horaires. Rien de plus a telecharger, donc : on lit ce qu'on
a deja.

Une limite du format : le corps de l'annonce est le plus souvent une image,
que 128 pixels de large ne sauraient rendre. Seul le titre est exploitable -
"Conference Vendredi 20h" -, ce qui suffit a dire qu'il se passe quelque
chose et quand.

Le texte vient d'un site tiers : il est ramene a ce que la police sait
ecrire, et tronque, avant d'approcher le panneau.
"""

import datetime

import font5x7

# Au-dela, le bandeau devient un roman : on prefere couper que faire attendre.
LONGUEUR_MAX = 44
COMBIEN_MAX = 3


def _date(valeur):
    """Lit une date Mawaqit ("2026-09-03 14:22" ou ISO), ou None."""
    if not valeur:
        return None
    texte = str(valeur).strip().replace("Z", "+00:00")
    for essai in (texte, texte.replace(" ", "T")):
        try:
            quand = datetime.datetime.fromisoformat(essai)
        except ValueError:
            continue
        return quand.replace(tzinfo=None) if quand.tzinfo is None \
            else quand.astimezone().replace(tzinfo=None)
    return None


def en_cours(annonce, maintenant):
    """Vrai si l'annonce est dans sa fenetre de diffusion.

    Les deux bornes sont facultatives cote Mawaqit : une annonce sans dates
    est permanente, et c'est le cas le plus frequent.
    """
    debut = _date(annonce.get("startDate"))
    fin = _date(annonce.get("endDate"))
    if debut and maintenant < debut:
        return False
    if fin and maintenant > fin:
        return False
    return True


def propre(titre):
    """Titre ramene a ce que la police 5x7 sait ecrire, et tronque."""
    texte = font5x7.affichable((titre or "").upper()).strip()
    texte = " ".join(texte.split())
    if len(texte) > LONGUEUR_MAX:
        texte = texte[:LONGUEUR_MAX - 1].rstrip() + "."
    return texte


def liste(conf, maintenant=None):
    """Titres des annonces a afficher, dans l'ordre de la mosquee."""
    if not conf:
        return ()
    maintenant = maintenant or datetime.datetime.now()
    titres = []
    for annonce in conf.get("annonces") or conf.get("announcements") or []:
        if not isinstance(annonce, dict) or not en_cours(annonce, maintenant):
            continue
        titre = propre(annonce.get("title"))
        if titre and titre not in titres:
            titres.append(titre)
        if len(titres) >= COMBIEN_MAX:
            break
    return tuple(titres)
