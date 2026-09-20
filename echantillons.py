"""Jeux d'essai des tests : reponses au format reel des APIs.

Sorti de test_hors_ligne.py, qui n'a plus que les verifications. Ces extraits
sont releves sur de vraies reponses, y compris leurs bizarreries : indicatifs
avec espaces, avion au sol, accolades dans les chaines du confData.
"""

import json

import panel
import prieresource
import transitions

# Extrait representatif d'une reponse adsb.lol /v2/point
ADSB_SAMPLE = {
    "ac": [
        {"hex": "39e68a", "flight": "AFR1234 ", "lat": 48.8600, "lon": 2.3634,
         "alt_baro": 34000, "gs": 442.1, "track": 271.4, "r": "F-GSQJ", "t": "B77W"},
        {"hex": "4ca8f1", "flight": "RYR51KM ", "lat": 49.0899, "lon": 2.7022,
         "alt_baro": 12000, "gs": 320.0, "track": 88.0, "r": "EI-DYZ", "t": "B738"},
        {"hex": "3c6444", "flight": "DLH9TX  ", "lat": 48.8579, "lon": 2.3552,
         "alt_baro": "ground", "gs": 12.0, "track": 5.0},
        {"hex": "abc123", "flight": "", "lat": 48.8569, "lon": 2.3532,
         "alt_baro": 30000},
    ]
}

# Extrait representatif d'une reponse adsbdb /v0/callsign
ADSBDB_SAMPLE = {
    "response": {
        "flightroute": {
            "callsign": "AFR1234",
            "callsign_icao": "AFR1234",
            "callsign_iata": "AF1234",
            "airline": {"name": "Air France", "icao": "AFR", "iata": "AF",
                        "country": "France", "country_iso": "FR"},
            "origin": {"iata_code": "CDG", "icao_code": "LFPG",
                       "municipality": "Paris", "name": "Charles de Gaulle",
                       "country_name": "France"},
            "destination": {"iata_code": "JFK", "icao_code": "KJFK",
                            "municipality": "New York",
                            "name": "John F Kennedy International",
                            "country_name": "United States"},
        }
    }
}

# Extrait representatif du confData embarque dans une page mawaqit.net.
# Structure et valeurs relevees sur une vraie page : calendar porte six
# horaires par jour (le chourouk est en deuxieme position), iqamaCalendar en
# porte cinq, soit un decalage "+N" soit une heure fixe.
def _mois_vides():
    return [{} for _ in range(12)]


_CAL = _mois_vides()
_CAL[0]["19"] = ["06:44", "08:36", "13:03", "15:07", "17:31", "19:07"]
_CAL[8]["19"] = ["05:54", "07:33", "13:45", "17:09", "19:59", "21:22"]
_CAL[8]["20"] = ["05:55", "07:34", "13:44", "17:07", "19:57", "21:19"]
_CAL[8]["25"] = ["06:02", "07:41", "13:43", "16:56", "19:43", "21:05"]

_IQ = _mois_vides()
_IQ[0]["19"] = ["+15", "+10", "+10", "+5", "19:20"]
_IQ[8]["19"] = ["+15", "+10", "+10", "+5", "+10"]
_IQ[8]["20"] = ["+15", "+10", "+10", "+5", "+10"]
_IQ[8]["25"] = ["+15", "+10", "+10", "+5", "+10"]

MAWAQIT_SAMPLE = {
    "name": "Mosquee de la Paix",
    "jumua": "13:30",
    "jumua2": "12:15",
    "timezone": "Europe/Paris",
    "calendar": _CAL,
    "iqamaCalendar": _IQ,
}

# La page reelle enrobe l'objet dans du JavaScript. On glisse volontairement
# une accolade et un guillemet echappe dans une chaine, c'est exactement ce
# qui casse un decoupage naif sur '}'.
MAWAQIT_HTML = (
    "<html><body><script>\n"
    "  var truc = {autre: 1};\n"
    "  confData = "
    + json.dumps({"name": "Mosquee {test} \"Exemple\"", "jumua": "13:30",
                  "calendar": _CAL, "iqamaCalendar": _IQ})
    + ";\n</script></body></html>"
)

