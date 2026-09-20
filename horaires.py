"""Lecture du calendrier de priere : quelle priere afficher, et quand.

Aucun acces reseau ici, que du calcul sur l'objet confData deja recupere par
prieresource.py. C'est la partie testable hors ligne, et celle dont depend
directement la mise en page du panneau.

Format du confData Mawaqit, releve sur une vraie page :
  calendar[mois][jour]       six horaires : fajr, chourouk, dohr, asr,
                             maghreb, icha
  iqamaCalendar[mois][jour]  cinq valeurs : soit un decalage "+10", soit une
                             heure fixe "19:20"
  jumua                      heure de la khoutba du vendredi
"""

import datetime
import unicodedata

# Noms affiches sur le panneau, dans l'ordre du calendrier Mawaqit
NOMS = ("FAJR", "DOHR", "ASR", "MAGHREB", "ICHA")
NOM_JOUMOUA = "JOUMOUA"


def nom_court(conf, slug):
    """Nom de mosquee affichable : ASCII, majuscules, assez court pour 128 px.

    Le champ 'name' de Mawaqit porte accents, guillemets et ville ; la police
    du panneau ne connait que l'ASCII. On prefere donc le premier mot du slug,
    qui est deja court et sans accent, et on ne retombe sur 'name' qu'a defaut.
    """
    if slug:
        return slug.split("-")[0].upper()[:9]
    texte = unicodedata.normalize("NFKD", (conf.get("name") or "").upper())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = "".join(c for c in texte if c.isalnum() or c == " ")
    return texte.strip()[:9]


def _minutes(hhmm):
    """'19:59' -> 1199 minutes depuis minuit. None si la valeur est illisible."""
    try:
        heure, minute = hhmm.split(":")
        return int(heure) * 60 + int(minute)
    except (AttributeError, ValueError):
        return None


def _hhmm(minutes):
    """1199 -> '19:59', en repliant les depassements de minuit."""
    minutes %= 24 * 60
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def day_times(conf, date):
    """Adhan et iqama d'une date donnee, en minutes depuis minuit.

    Renvoie une liste de cinq dicts {nom, adhan, iqama}, plus le chourouk.
    """
    mois = conf["calendar"][date.month - 1]
    jour = mois.get(str(date.day))
    if not jour:
        return None, None

    adhans = [_minutes(v) for v in jour]
    chourouk = adhans[1] if len(adhans) > 5 else None
    # calendar = [fajr, chourouk, dohr, asr, maghreb, icha] -> on retire chourouk
    adhans = [adhans[0]] + adhans[2:] if len(adhans) > 5 else adhans

    try:
        iqamas_bruts = conf["iqamaCalendar"][date.month - 1].get(str(date.day)) or []
    except (KeyError, IndexError, AttributeError):
        iqamas_bruts = []

    prieres = []
    for index, nom in enumerate(NOMS):
        adhan = adhans[index] if index < len(adhans) else None
        if adhan is None:
            continue
        iqama = None
        brut = iqamas_bruts[index] if index < len(iqamas_bruts) else None
        if isinstance(brut, str) and brut:
            if brut[0] in "+-":
                try:
                    iqama = adhan + int(brut)
                except ValueError:
                    iqama = None
            else:
                iqama = _minutes(brut)
        if iqama is None:
            iqama = adhan
        prieres.append({"nom": nom, "adhan": adhan, "iqama": iqama})

    # Vendredi : la priere de midi devient la Joumoua. L'heure annoncee par la
    # mosquee fait foi pour les deux, car la khoutba commence souvent avant le
    # dohr astronomique - garder ce dernier donnerait une iqama anterieure a
    # son propre adhan.
    if date.weekday() == 4 and len(prieres) > 1:
        joumoua = _minutes(conf.get("jumua") or "")
        prieres[1]["nom"] = NOM_JOUMOUA
        if joumoua is not None:
            prieres[1]["adhan"] = joumoua
            prieres[1]["iqama"] = joumoua

    return prieres, chourouk


def format_restant(minutes):
    """Duree courte tenant sur le panneau : '12 MIN' ou '7H20'."""
    if minutes < 0:
        minutes = 0
    if minutes < 60:
        return "%d MIN" % minutes
    return "%dH%02d" % (minutes // 60, minutes % 60)


def next_prayer(conf, now=None, avant_min=3, apres_min=5):
    """La priere a afficher, et s'il faut couper l'avion pour elle.

    Tant que l'iqama n'est pas passee on reste sur la priere en cours : entre
    l'adhan et l'iqama, ce qui interesse c'est le temps qu'il reste pour
    rejoindre la mosquee, pas la priere suivante.
    """
    now = now or datetime.datetime.now()
    aujourd_hui = now.date()
    maintenant = now.hour * 60 + now.minute

    prieres, chourouk = day_times(conf, aujourd_hui)
    if not prieres:
        return None

    # La journee entiere, pour l'ecran qui affiche les cinq horaires
    jour = [{"nom": p["nom"], "adhan": _hhmm(p["adhan"])} for p in prieres]

    for rang, priere in enumerate(prieres):
        if maintenant >= priere["iqama"] + apres_min:
            continue
        if maintenant < priere["adhan"]:
            phase, restant = "adhan", priere["adhan"] - maintenant
        elif maintenant < priere["iqama"]:
            phase, restant = "iqama", priere["iqama"] - maintenant
        else:
            phase, restant = "encours", 0
        return {
            "nom": priere["nom"],
            "adhan": _hhmm(priere["adhan"]),
            "iqama": _hhmm(priere["iqama"]),
            "phase": phase,
            "restant_min": restant,
            "restant": format_restant(restant),
            "chourouk": _hhmm(chourouk) if chourouk is not None else "",
            "prise_main": phase != "adhan" or restant <= avant_min,
            "demain": False,
            "jour": jour,
            "rang": rang,
        }

    # Toutes les prieres du jour sont passees : on annonce le Fajr de demain
    demain = aujourd_hui + datetime.timedelta(days=1)
    prieres_demain, _ = day_times(conf, demain)
    if not prieres_demain:
        return None
    fajr = prieres_demain[0]
    restant = fajr["adhan"] + 24 * 60 - maintenant
    return {
        "nom": fajr["nom"],
        "adhan": _hhmm(fajr["adhan"]),
        "iqama": _hhmm(fajr["iqama"]),
        "phase": "adhan",
        "restant_min": restant,
        "restant": format_restant(restant),
        "chourouk": "",
        "prise_main": False,
        "demain": True,
        # le tableau reste celui du jour ecoule : a 23 h, ce sont encore les
        # horaires que l'on veut relire, pas ceux de demain
        "jour": jour,
        "rang": -1,
    }
