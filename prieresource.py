"""Recuperation des horaires de priere de la mosquee, depuis Mawaqit.

Mawaqit n'expose pas d'API publique. En revanche chaque page de mosquee
embarque un objet JSON "confData" dans son HTML, qui contient le calendrier
annuel complet : adhan jour par jour, iqama jour par jour, joumoua.

On le lit donc une fois par jour et on le garde sur disque. Le calendrier
couvrant l'annee entiere, le panneau continue d'afficher les bons horaires
meme si le reseau tombe pendant des semaines.

L'interpretation du calendrier est dans horaires.py ; ici il n'y a que le
reseau et le cache, comme flightsource.py pour les vols.

Source : https://mawaqit.net/fr/<slug>   (slug = fin de l'URL de la mosquee)
Uniquement la bibliotheque standard, aucun pip install necessaire.
"""

import datetime
import json
import time
import urllib.error

import annonces
import horaires
import stockage
import telechargement

MAWAQIT_URL = "https://mawaqit.net/fr/%s"

CONF_TTL = 24 * 3600  # le calendrier est annuel, un rechargement par jour suffit
CACHE_FILE = "prieres_cache.json"


def _extract_conf(html):
    """Isole l'objet confData du HTML de la page.

    Analyse a accolades equilibrees, en ignorant celles qui se trouvent dans
    une chaine JSON : un simple decoupage sur '}' casserait sur les noms de
    mosquee contenant des accolades ou des guillemets echappes.
    """
    start = html.index("confData")
    start = html.index("{", start)
    depth, i, in_str, esc = 0, start, False, False
    while i < len(html):
        char = html[i]
        if in_str:
            if esc:
                esc = False
            elif char == "\\":
                esc = True
            elif char == '"':
                in_str = False
        elif char == '"':
            in_str = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(html[start:i + 1])
        i += 1
    raise ValueError("confData incomplet")


def fetch_conf(slug, timeout=telechargement.DELAI_MAX):
    """Telecharge la page de la mosquee et en extrait confData."""
    return _extract_conf(telechargement.lire_texte(MAWAQIT_URL % slug,
                                                   timeout))


class PrayerCache:
    """Cache disque du confData, pour ne charger la page qu'une fois par jour."""

    def __init__(self, path=CACHE_FILE):
        self.path = path
        self.data = stockage.lit_json(path)

    def get(self, slug, ignore_ttl=False):
        entry = self.data.get(slug)
        if not entry:
            return None
        if not ignore_ttl and time.time() - entry.get("ts", 0) > CONF_TTL:
            return None
        return entry.get("conf")

    def put(self, slug, conf):
        self.data[slug] = {"ts": time.time(), "conf": conf}
        stockage.ecrit_json_atomique(self.path, self.data)


def load_conf(slug, cache, erreurs=None):
    """confData frais si possible, sinon la derniere version connue.

    Un cache perime vaut mieux qu'un ecran vide : le calendrier est annuel,
    donc meme vieux de plusieurs jours il reste juste. L'echec n'est pas
    tu pour autant : il part dans erreurs, si l'appelant en fournit une.
    """
    conf = cache.get(slug)
    if conf is not None:
        return conf
    try:
        conf = fetch_conf(slug)
    except (urllib.error.URLError, ValueError, KeyError, OSError) as exc:
        if erreurs is not None:
            erreurs.append(exc)
        return cache.get(slug, ignore_ttl=True)
    cache.put(slug, conf)
    return conf


def depuis_conf(conf, config, slug, now=None):
    """Priere courante a partir d'un confData deja en main. Aucun reseau.

    Separe de poll() parce que la ponctualite l'exige : le reseau ne se
    sollicite qu'une fois par jour, mais la phase de la priere, elle, doit
    etre exacte a la seconde. L'adhan sonne au passage d'une phase a l'autre,
    et la recalculer toutes les douze secondes le ferait retentir jusqu'a
    douze secondes apres l'heure de la mosquee.

    Ce calcul est pur et tient en quelques microsecondes : on le refait a
    chaque demande plutot que de garder un instantane qui vieillit.
    """
    if not conf:
        return None
    annonces_mosquee = annonces.liste(conf, now)
    info = horaires.next_prayer(conf, now,
                                avant_min=config.get("priere_avant_min", 3),
                                apres_min=config.get("priere_apres_min", 5))
    if info:
        info["mosquee"] = horaires.nom_court(conf, slug)
        # L'heure est calculee ici et envoyee telle quelle a l'ESP32, qui n'a
        # ni horloge sauvegardee ni client NTP a regler.
        info["heure"] = (now or datetime.datetime.now()).strftime("%H:%M")
        # Les annonces viennent du meme confData : rien de plus a telecharger
        info["annonces"] = annonces_mosquee
    return info


def poll(config, cache, now=None):
    """Un cycle complet : confData (cache ou reseau) puis priere courante."""
    slug = config.get("mosquee_slug")
    if not slug:
        return None
    return depuis_conf(load_conf(slug, cache), config, slug, now)
