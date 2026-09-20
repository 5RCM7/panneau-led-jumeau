"""Quel son le panneau doit jouer, et a quel volume.

La politique vit ici, en Python, comme la rotation des ecrans : le firmware
se contente d'obeir. Il recoit un son, un volume, et une cle ; il joue quand
la cle change. Aucune regle n'est rejouee cote C, donc aucune ne peut y
diverger.

Ce qui sonne, et quand :

    a l'heure de la priere   l'adhan             /mp3/0001.mp3
    a l'heure de l'iqama     la priere commence  /mp3/0002.mp3

Le nom des phases de horaires.py peut egarer, parce qu'il designe ce qu'on
ATTEND et non ce qui vient d'arriver : on est en phase "adhan" tant que
l'adhan n'a pas sonne, et en phase "iqama" une fois qu'il a sonne et qu'on
attend l'iqama. Entrer dans une phase, c'est donc franchir l'heure de la
precedente - d'ou la table SON_A_L_ENTREE ci-dessous, qu'il vaut mieux lire
deux fois avant d'y toucher.

Le materiel est un DFPlayer Mini, qui lit ses pistes sur sa propre microSD :

    /mp3/0001.mp3   l'adhan
    /mp3/0002.mp3   le signal court de l'iqama

Jumeau de firmware/audio.h.
"""

# Pistes sur la carte, memes valeurs dans firmware/audio.h
SON_AUCUN = 0
SON_ADHAN = 1
SON_IQAMA = 2

# Volume du DFPlayer, de 0 a 30. Au-dela de 25 le petit ampli sature.
VOLUME_MAX = 30
VOLUME_JOUR = 22
VOLUME_NUIT = 12

# Phase dans laquelle on vient d'entrer -> son qui marque ce passage.
# Entrer en phase "iqama" signifie que l'heure de la priere vient d'etre
# atteinte : c'est l'adhan qui retentit. Entrer en "encours" signifie que
# l'heure de l'iqama est arrivee, et que la priere commence.
SON_A_L_ENTREE = {
    "iqama": SON_ADHAN,      # l'heure de la priere vient de sonner
    "encours": SON_IQAMA,    # la priere commence
}


def volume(config, de_nuit=False):
    """Volume a envoyer au DFPlayer, borne a la plage qu'il accepte.

    Meme plage nocturne que la luminosite : un panneau qui s'assombrit la
    nuit et qui hurle quand meme n'aurait aucun sens.
    """
    brut = config.get("volume_nuit", VOLUME_NUIT) if de_nuit \
        else config.get("volume_jour", VOLUME_JOUR)
    try:
        return max(0, min(VOLUME_MAX, int(brut)))
    except (TypeError, ValueError):
        return VOLUME_NUIT if de_nuit else VOLUME_JOUR


def cue(prieres):
    """Cle d'unicite du son : elle ne change qu'au passage d'une phase.

    C'est elle qui evite qu'un son se rejoue a chaque interrogation de la
    passerelle, trois secondes apres la precedente.
    """
    if not prieres:
        return ""
    nom = prieres.get("nom") or ""
    phase = prieres.get("phase") or ""
    if phase not in SON_A_L_ENTREE:
        return ""
    return "%s:%s" % (nom, phase)


def son(prieres, config=None):
    """Piste a jouer pour la phase courante, SON_AUCUN s'il n'y en a pas."""
    config = config or {}
    if not config.get("audio_actif", True):
        return SON_AUCUN
    if not prieres or prieres.get("demain"):
        return SON_AUCUN
    return SON_A_L_ENTREE.get(prieres.get("phase") or "", SON_AUCUN)


def etat(prieres, config=None, de_nuit=False):
    """Ce que la passerelle envoie au panneau : son, volume, et cle.

    Le volume part meme quand il n'y a rien a jouer : le DFPlayer le retient
    d'une piste a l'autre, et le regler au moment de jouer serait trop tard.
    """
    config = config or {}
    piste = son(prieres, config)
    return {
        "son": piste,
        "cue": cue(prieres) if piste else "",
        "volume": volume(config, de_nuit),
    }
