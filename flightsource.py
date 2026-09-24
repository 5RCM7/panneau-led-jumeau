"""Passerelle de donnees : quel avion est au-dessus de la maison, et ou va-t-il.

Sources, toutes gratuites et sans cle :
  - positions   : https://api.adsb.lol/v2/point/{lat}/{lon}/{rayon_nm}
  - routes      : https://api.adsbdb.com/v0/callsign/{indicatif}
  - repli route : https://hexdb.io/callsign-route?callsign={indicatif}

Uniquement la bibliotheque standard, aucun pip install necessaire.
"""

import json
import math
import threading
import time
import urllib.error
import urllib.parse

import font5x7
import stockage
import telechargement

ADSB_POINT = "https://api.adsb.lol/v2/point/%s/%s/%s"
ADSBDB_CALLSIGN = "https://api.adsbdb.com/v0/callsign/%s"
ADSBDB_AIRCRAFT = "https://api.adsbdb.com/v0/aircraft/%s"
HEXDB_ROUTE = "https://hexdb.io/callsign-route?callsign=%s"

# Prefixe des cles d'appareil dans le cache, pour ne pas les confondre avec
# les routes qui y sont rangees par indicatif.
CLE_APPAREIL = "AV:"

ROUTE_TTL = 12 * 3600  # une route de vol change rarement dans la journee
CACHE_FILE = "routes_cache.json"
DELAI_S = telechargement.DELAI_MAX  # par appel, connexion et lecture comprises


def _get_json(url, timeout=None):
    return json.loads(telechargement.lire_texte(
        url, timeout or DELAI_S, {"Accept": "application/json"}))


def _get_text(url, timeout=None):
    return telechargement.lire_texte(url, timeout or DELAI_S).strip()


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class RouteCache:
    """Cache disque des routes, pour ne pas matraquer adsbdb.

    Les entrees perimees sont purgees au chargement et a chaque ajout : sans
    cela le fichier gardait chaque indicatif jamais croise, grossissait sans
    fin, et etait reecrit en entier a chaque nouvel avion. L'ecriture est
    atomique, cf. stockage.py.
    """

    def __init__(self, path=CACHE_FILE):
        self.path = path
        self.lock = threading.Lock()
        self.data = stockage.lit_json(path)
        self._purge()

    def _purge(self, maintenant=None):
        """Retire les entrees perimees. Renvoie combien il en est parti."""
        limite = (maintenant or time.time()) - ROUTE_TTL
        vieilles = [cle for cle, entree in self.data.items()
                    if not isinstance(entree, dict)
                    or entree.get("ts", 0) < limite]
        for cle in vieilles:
            del self.data[cle]
        return len(vieilles)

    def get(self, key):
        with self.lock:
            entry = self.data.get(key)
        if not entry:
            return None
        if time.time() - entry.get("ts", 0) > ROUTE_TTL:
            return None
        return entry.get("route")

    def put(self, key, route):
        with self.lock:
            self._purge()
            self.data[key] = {"ts": time.time(), "route": route}
            copie = dict(self.data)
        stockage.ecrit_json_atomique(self.path, copie)


def fetch_nearby(lat, lon, radius_nm):
    """Renvoie la liste brute des aeronefs dans le rayon donne."""
    url = ADSB_POINT % (lat, lon, radius_nm)
    payload = _get_json(url)
    return payload.get("ac") or []


def _altitude_ft(aircraft):
    alt = aircraft.get("alt_baro")
    if alt in (None, "ground"):
        return None
    try:
        return int(alt)
    except (TypeError, ValueError):
        return None


def pick_overhead(aircraft_list, lat, lon, min_alt_ft=1000, max_dist_km=20,
                  courant=None, marge_km=0.0):
    """Choisit l'avion le plus proche du point d'observation.

    Hysteresis : l'avion courant (son indicatif) garde l'ecran tant qu'il
    reste eligible, sauf si un autre est plus proche de plus de marge_km.
    Sans elle, deux avions a distance voisine se relaient a chaque sondage,
    et chaque relais relance l'annonce d'arrivee.
    """
    courant = (courant or "").strip().upper()
    best = None
    best_dist = None
    garde = None
    garde_dist = None
    for aircraft in aircraft_list:
        try:
            a_lat = float(aircraft["lat"])
            a_lon = float(aircraft["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        altitude = _altitude_ft(aircraft)
        if altitude is None or altitude < min_alt_ft:
            continue
        callsign = (aircraft.get("flight") or "").strip()
        if not callsign:
            continue
        distance = haversine_km(lat, lon, a_lat, a_lon)
        if distance > max_dist_km:
            continue
        if best_dist is None or distance < best_dist:
            best, best_dist = aircraft, distance
        if courant and callsign.upper() == courant:
            garde, garde_dist = aircraft, distance
    if best is None:
        return None, None
    if garde is not None and best_dist > garde_dist - marge_km:
        return garde, garde_dist
    return best, best_dist


def lookup_route(callsign, cache):
    """Indicatif -> compagnie, aeroport de depart, aeroport d'arrivee."""
    callsign = callsign.strip().upper()
    cached = cache.get(callsign)
    if cached is not None:
        return cached

    route = {}
    try:
        payload = _get_json(ADSBDB_CALLSIGN % urllib.parse.quote(callsign))
        info = (payload.get("response") or {}).get("flightroute") or {}
        airline = info.get("airline") or {}
        origin = info.get("origin") or {}
        destination = info.get("destination") or {}
        route = {
            "airline_name": airline.get("name"),
            "airline_icao": airline.get("icao"),
            "airline_iata": airline.get("iata"),
            "origin": origin.get("iata_code"),
            "origin_city": origin.get("municipality"),
            "destination": destination.get("iata_code"),
            "destination_city": destination.get("municipality"),
            "destination_name": destination.get("name"),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError):
        route = {}

    if not route.get("destination"):
        route.update(_lookup_route_hexdb(callsign))

    if route.get("destination") or route.get("airline_name"):
        cache.put(callsign, route)
    return route


def _lookup_route_hexdb(callsign):
    """Repli hexdb.io, qui renvoie une chaine du type 'LFPG-KJFK'."""
    try:
        text = _get_text(HEXDB_ROUTE % urllib.parse.quote(callsign))
    except (urllib.error.URLError, urllib.error.HTTPError):
        return {}
    if not text or "-" not in text or len(text) > 40:
        return {}
    parts = text.split("-")
    if len(parts) < 2:
        return {}
    return {"origin": parts[0].strip()[:4], "destination": parts[-1].strip()[:4]}


def lookup_aircraft(registration, cache):
    """Immatriculation -> marque et modele en clair, ou {} si inconnu.

    adsbdb ne connait pas tous les appareils : une immatriculation recente ou
    un avion d'affaires renvoie 404. L'appelant retombe alors sur le code
    type transmis par l'avion lui-meme (B77W, A20N), moins parlant mais
    toujours present.
    """
    registration = (registration or "").strip().upper()
    if not registration:
        return {}
    cle = CLE_APPAREIL + registration
    connu = cache.get(cle)
    if connu is not None:
        return connu

    appareil = {}
    try:
        payload = _get_json(ADSBDB_AIRCRAFT % urllib.parse.quote(registration))
        info = (payload.get("response") or {}).get("aircraft") or {}
        appareil = {
            "manufacturer": info.get("manufacturer"),
            "type": info.get("type"),
            "icao_type": info.get("icao_type"),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError,
            KeyError, AttributeError):
        appareil = {}

    if appareil.get("manufacturer") or appareil.get("type"):
        cache.put(cle, appareil)
    return appareil


def nom_appareil(appareil, code_type):
    """'Boeing' + '777 328ER' -> 'BOEING 777 328ER'.

    Repli sur le code type de l'avion quand adsbdb ne le connait pas, et
    chaine vide quand on n'a rien du tout.
    """
    marque = (appareil or {}).get("manufacturer") or ""
    modele = (appareil or {}).get("type") or ""
    complet = " ".join(p for p in (marque, modele) if p).strip()
    return (complet or code_type or "").upper()


def build_flight(aircraft, distance_km, route, appareil=None):
    """Assemble l'objet unique que consomment le simulateur et l'ESP32."""
    altitude = _altitude_ft(aircraft)
    level = "FL%03d" % (altitude // 100) if altitude else ""
    callsign = (aircraft.get("flight") or "").strip().upper()

    # Les APIs renvoient des noms accentues (Sao Paulo, Nimes, Malaga). La
    # police du panneau ne connait que l'ASCII et les rendrait en '?', aussi
    # bien dans le simulateur que sur l'ESP32 qui recoit ces champs tels
    # quels. On les nettoie ici, a la source, plutot qu'a chaque affichage.
    def propre(valeur):
        return font5x7.affichable(valeur) if valeur else valeur

    flight = {
        "callsign": callsign,
        "hex": aircraft.get("hex"),
        "registration": aircraft.get("r"),
        "type": aircraft.get("t"),
        "aircraft": propre(nom_appareil(appareil, aircraft.get("t"))),
        "altitude_ft": altitude,
        "level": level,
        "speed_kt": aircraft.get("gs"),
        "track": aircraft.get("track"),
        "distance_km": round(distance_km, 1) if distance_km is not None else None,
        "airline_name": propre(route.get("airline_name")),
        "airline_icao": route.get("airline_icao") or (callsign[:3] if len(callsign) > 3 else None),
        "airline_iata": route.get("airline_iata"),
        "origin": route.get("origin"),
        "origin_city": propre(route.get("origin_city")),
        "destination": route.get("destination"),
        "destination_city": propre(route.get("destination_city")
                                    or route.get("destination_name")),
        "updated": time.time(),
    }
    return flight


def poll(config, cache, courant=None):
    """Un cycle complet : positions, selection, enrichissement.

    courant est l'indicatif deja a l'ecran, que l'hysteresis favorise.
    """
    lat = config["latitude"]
    lon = config["longitude"]
    aircraft_list = fetch_nearby(lat, lon, config.get("search_radius_nm", 15))
    aircraft, distance = pick_overhead(
        aircraft_list, lat, lon,
        min_alt_ft=config.get("min_altitude_ft", 1000),
        max_dist_km=config.get("max_distance_km", 20),
        courant=courant,
        marge_km=config.get("bascule_km", 1.0),
    )
    if aircraft is None:
        return None
    route = lookup_route(aircraft.get("flight", ""), cache)
    appareil = lookup_aircraft(aircraft.get("r"), cache)
    return build_flight(aircraft, distance, route, appareil)
