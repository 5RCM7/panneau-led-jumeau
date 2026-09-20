"""Quota Claude Code : lecture d'usage.json, et calcul de ce qu'il reste.

Il n'y a pas d'API a interroger. Les chiffres du quota ne sont lisibles que
depuis Claude Code lui-meme, par sa commande /usage ; ni la passerelle ni
l'ESP32 ne savent les demander a Anthropic. On passe donc par un fichier,
usage.json, ecrit par maj_usage.py quand on releve les chiffres.

Le fichier ne contient que ce qui a ete releve. Tout ce qui se deduit de
l'horloge - le temps restant avant remise a zero, la peremption d'un
releve - se calcule ici, a chaque lecture : un chiffre vieux d'une heure
reste juste, son compte a rebours non.

Une fenetre dont l'heure de remise a zero est passee devient inconnue, et
non pas nulle : la consommation a repris depuis, on ne sait simplement plus
ou elle en est.

Format d'usage.json, cf. usage.exemple.json :

    {"plan": "Pro",
     "releve": "2026-09-20T11:55:00",
     "fenetres": [{"cle": "5H", "utilise": 39,
                   "reset": "2026-09-20T16:20:00"},
                  {"cle": "7J", "utilise": 48,
                   "reset": "2026-09-25T19:00:00"}]}
"""

import datetime
import json
import os

FICHIER = "usage.json"

# Au-dela, le releve est trop vieux pour qu'on l'affiche : un quota de la
# semaine derniere n'apprend rien, et vaut moins qu'un ecran en moins.
AGE_MAX_HEURES = 24


def _date(valeur):
    """Lit une date ISO, avec ou sans fuseau, ou renvoie None."""
    if not valeur:
        return None
    texte = str(valeur).strip().replace("Z", "+00:00")
    try:
        quand = datetime.datetime.fromisoformat(texte)
    except ValueError:
        return None
    # On travaille en heure locale : le panneau est dans un salon, pas en UTC
    if quand.tzinfo is not None:
        quand = quand.astimezone().replace(tzinfo=None)
    return quand


def format_reste(quand, maintenant):
    """Temps restant avant une echeance, en quatre caracteres au plus.

    Quatre caracteres, parce que la ligne est deja pleine : le libelle, la
    jauge et le pourcentage prennent le reste. D'ou les formes abregees,
    qui perdent en precision a mesure que l'echeance s'eloigne - ce qui
    tombe bien, c'est aussi la ou la precision importe le moins.
    """
    if not quand:
        return ""
    minutes = int((quand - maintenant).total_seconds() // 60)
    if minutes <= 0:
        return ""
    if minutes < 60:
        return "%dM" % minutes
    heures, reste = divmod(minutes, 60)
    if heures < 24:
        return "%dH%02d" % (heures, reste) if heures < 10 else "%dH" % heures
    jours, heures = divmod(heures, 24)
    if jours < 10 and heures < 10:
        return "%dJ%dH" % (jours, heures)
    return "%dJ" % jours


def lire(chemin):
    """Contenu brut d'usage.json, ou None s'il est absent ou illisible."""
    try:
        with open(chemin, encoding="utf-8") as handle:
            return json.load(handle)
    except (IOError, OSError, ValueError):
        return None


def poll(config, chemin=None, maintenant=None):
    """Etat du quota, tel que l'ecran l'attend, ou None s'il n'y a rien.

    None fait sauter l'ecran dans la rotation, comme une meteo absente :
    mieux vaut un ecran en moins qu'un chiffre faux sur le mur.
    """
    if chemin is None:
        chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              FICHIER)
    brut = lire(chemin)
    if not brut:
        return None

    maintenant = maintenant or datetime.datetime.now()
    age_max = config.get("usage_age_max_heures", AGE_MAX_HEURES)
    releve = _date(brut.get("releve"))
    if releve is None:
        return None
    age = (maintenant - releve).total_seconds() / 3600.0
    if age > age_max or age < -1:
        return None

    fenetres = brut.get("fenetres") or []
    if len(fenetres) < 2:
        return None

    info = {"plan": (brut.get("plan") or "").upper(),
            "age_min": int(age * 60)}
    for suffixe, fenetre in zip(("a", "b"), fenetres[:2]):
        reset = _date(fenetre.get("reset"))
        expiree = reset is not None and reset <= maintenant
        try:
            utilise = int(fenetre.get("utilise"))
        except (TypeError, ValueError):
            utilise = None
        info["cle_" + suffixe] = (fenetre.get("cle") or "").upper()
        # Expiree : la consommation a repris, on ne sait plus ou elle en est
        info["restant_" + suffixe] = (None if expiree or utilise is None
                                      else max(0, min(100, 100 - utilise)))
        info["reset_" + suffixe] = format_reste(reset, maintenant)

    # Les deux fenetres inconnues : l'ecran n'apprendrait plus rien
    if info["restant_a"] is None and info["restant_b"] is None:
        return None
    return info
