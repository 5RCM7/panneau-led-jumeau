"""Meteo courante du domicile, depuis Open-Meteo.

Gratuite, sans cle ni inscription, comme les autres sources du projet. Un seul
appel donne la temperature, le ressenti, le vent, le code WMO du temps qu'il
fait, et s'il fait jour - de quoi choisir entre un soleil et une lune.

Source : https://api.open-meteo.com/v1/forecast
Uniquement la bibliotheque standard, aucun pip install necessaire.
"""

import datetime
import json
import os
import time
import urllib.error
import urllib.request

USER_AGENT = "jumeau-panneau-led/1.0 (projet personnel)"
OPEN_METEO = ("https://api.open-meteo.com/v1/forecast"
              "?latitude=%s&longitude=%s"
              "&current=temperature_2m,apparent_temperature,weather_code,"
              "wind_speed_10m,is_day"
              # six heures de precipitations par quart d'heure : de quoi
              # prevenir avant de sortir, sans alourdir l'appel
              "&minutely_15=precipitation&forecast_minutely_15=24"
              "&timezone=auto")

# Une averse commence a compter a partir de ce cumul sur un quart d'heure :
# en dessous, c'est trois gouttes et une alerte pour rien.
PLUIE_SEUIL_MM = 0.2
# Au-dela, l'averse est trop loin pour changer quoi que ce soit a la journee.
PLUIE_HORIZON_MIN = 120

METEO_TTL = 900  # Open-Meteo rafraichit au quart d'heure, inutile d'insister
CACHE_FILE = "meteo_cache.json"

# Codes WMO regroupes par icone. Ce que le panneau montre est grossier a
# dessein : sur 17 pixels de large, bruine et pluie ne se distinguent pas.
_TEMPS = (
    ((0,), "CLAIR", "soleil"),
    ((1,), "PEU NUAGEUX", "eclaircie"),
    ((2,), "ECLAIRCIES", "eclaircie"),
    ((3,), "COUVERT", "nuage"),
    ((45, 48), "BROUILLARD", "nuage"),
    ((51, 53, 55, 56, 57), "BRUINE", "pluie"),
    ((61, 63, 65, 66, 67, 80, 81, 82), "PLUIE", "pluie"),
    ((71, 73, 75, 77, 85, 86), "NEIGE", "neige"),
    ((95, 96, 99), "ORAGE", "orage"),
)


def decrit(code, jour=True):
    """Code WMO -> (texte affichable, nom d'icone)."""
    for codes, texte, icone in _TEMPS:
        if code in codes:
            # de nuit, un ciel clair merite une lune et non un soleil
            if icone == "soleil" and not jour:
                icone = "lune"
            return texte, icone
    return "TEMPS INCONNU", "nuage"


class MeteoCache:
    """Cache disque, pour ne pas interroger Open-Meteo a chaque image."""

    def __init__(self, path=CACHE_FILE):
        self.path = path
        self.data = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    self.data = json.load(handle)
            except Exception:
                self.data = {}

    def get(self, cle, ignore_ttl=False):
        entree = self.data.get(cle)
        if not entree:
            return None
        if not ignore_ttl and time.time() - entree.get("ts", 0) > METEO_TTL:
            return None
        return entree.get("meteo")

    def put(self, cle, meteo):
        self.data[cle] = {"ts": time.time(), "meteo": meteo}
        try:
            with open(self.path, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle)
        except Exception:
            pass


def fetch(lat, lon, timeout=10):
    """Interroge Open-Meteo et renvoie le courant et la pluie a venir."""
    requete = urllib.request.Request(OPEN_METEO % (lat, lon),
                                     headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(requete, timeout=timeout) as reponse:
        charge = json.loads(reponse.read().decode("utf-8", "replace"))
    brut = dict(charge.get("current") or {})
    # La prevision voyage telle quelle dans le cache : ce sont des heures
    # absolues, donc le "dans combien de temps" se recalcule a chaque
    # lecture. Un cache d'un quart d'heure rendrait faux un delai fige.
    brut["_quarts"] = charge.get("minutely_15") or {}
    return brut


def prochaine_pluie(quarts, maintenant, seuil=PLUIE_SEUIL_MM,
                    horizon=PLUIE_HORIZON_MIN):
    """Minutes avant la prochaine averse, ou None s'il n'en vient pas.

    Renvoie aussi l'heure de debut : "dans 40 min" se lit d'un coup, mais
    "a 17h30" se retient mieux quand on prepare sa sortie.
    """
    heures = (quarts or {}).get("time") or []
    pluies = (quarts or {}).get("precipitation") or []
    for texte, mm in zip(heures, pluies):
        try:
            quand = datetime.datetime.fromisoformat(texte)
            cumul = float(mm)
        except (TypeError, ValueError):
            continue
        if cumul < seuil:
            continue
        minutes = int(round((quand - maintenant).total_seconds() / 60.0))
        if minutes < 0 or minutes > horizon:
            continue
        return max(0, minutes), quand.strftime("%H:%M")
    return None, ""


def _arrondi(valeur):
    """Temperature affichable : entier signe, ou None si illisible."""
    try:
        return int(round(float(valeur)))
    except (TypeError, ValueError):
        return None


def poll(config, cache, now=None):
    """Un cycle complet : meteo (cache ou reseau) mise en forme pour l'ecran."""
    lat, lon = config.get("latitude"), config.get("longitude")
    if lat is None or lon is None:
        return None

    cle = "%s,%s" % (lat, lon)
    brut = cache.get(cle)
    if brut is None:
        try:
            brut = fetch(lat, lon)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError,
                OSError):
            # un cache perime vaut mieux qu'un ecran vide : la temperature
            # d'il y a une heure reste plus juste que pas de temperature
            brut = cache.get(cle, ignore_ttl=True)
        else:
            cache.put(cle, brut)
    if not brut:
        return None

    jour = bool(brut.get("is_day", 1))
    texte, icone = decrit(brut.get("weather_code"), jour)
    vent = _arrondi(brut.get("wind_speed_10m"))
    # l'heure accompagne la meteo jusqu'a l'ESP32, qui n'a pas d'horloge
    maintenant = now or datetime.datetime.now()
    pluie_min, pluie_heure = prochaine_pluie(
        brut.get("_quarts"), maintenant,
        config.get("pluie_seuil_mm", PLUIE_SEUIL_MM),
        config.get("pluie_horizon_min", PLUIE_HORIZON_MIN))
    # Annoncer la pluie pendant qu'elle tombe n'apprend rien : l'icone le dit
    if icone in ("pluie", "orage"):
        pluie_min, pluie_heure = None, ""
    return {
        "pluie_min": pluie_min,
        "pluie_heure": pluie_heure,
        "heure": maintenant.strftime("%H:%M"),
        "temperature": _arrondi(brut.get("temperature_2m")),
        "ressenti": _arrondi(brut.get("apparent_temperature")),
        "vent_kmh": vent,
        "code": brut.get("weather_code"),
        "texte": texte,
        "icone": icone,
        "jour": jour,
        "lieu": (config.get("meteo_lieu") or "").upper(),
    }
