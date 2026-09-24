"""Charge utile pour l'ESP32, et composition de l'image courante.

Separe de server.py : ce sont les deux endroits ou les ecrans se rejoignent,
et ils ne dependent pas du serveur HTTP.

Taille de la charge utile : le budget etait de 400 octets du temps ou seuls
les vols circulaient. Chaque ecran y a ajoute son bloc ; tous remplis
jusqu'a leur tampon C (annonces, quota et audio compris), le pire cas monte
a ~930 octets, et une charge ordinaire en fait ~560. Le plafond est releve a
BUDGET_OCTETS plutot que de tordre le format : ArduinoJson v7 alloue sur le
tas, environ trois fois la taille du JSON, soit ~3 Ko sur les ~260 Ko libres
de l'ESP32. La contrainte reelle n'est pas la ; le test 21 mesure le vrai
pire cas, et doit etre complete a chaque nouveau bloc.
"""

import os

import ecran_adkar
import ecran_alerte
import ecran_annonces
import ecran_claude
import ecran_heure
import ecran_horaires
import ecran_meteo
import ecran_prieres
import icones_meteo
import panel
import transitions

HERE = os.path.dirname(os.path.abspath(__file__))

BUDGET_OCTETS = 1024

# Separateur des titres d'annonce dans la charge utile, cf. ecran_annonces.h
SEP_ANNONCES = "|"

# Une annonce n'est qu'un habillage : l'ecran de fond est ce que le firmware
# doit connaitre, il rejoue l'annonce de son cote.
ECRAN_DE_FOND = {
    "alerte": "vol",
    "alerte_priere": "priere",
    "alerte_meteo": "meteo",
}

# Ecrans que le firmware impose de lui-meme : la passerelle ne peut pas
# signaler son propre silence.
ECRANS_LOCAUX = ("liaison",)

def compact_flight(flight, prieres=None, ecran=None, meteo=None, heure=None,
                   rang_adkar=None, usage=None, son=None):
    """Charge utile minuscule pour l'ESP32 : quelques centaines d'octets.

    'sc' porte l'ecran a afficher. L'arbitrage entre vol et priere est fait
    ici, une seule fois : le firmware se contente d'obeir, ce qui evite que
    les deux cotes du jumeau divergent sur la regle de priorite.
    """
    payload = {"ok": False}
    if flight:
        payload = {
            "ok": True,
            "cs": flight.get("callsign") or "",
            "al": flight.get("airline_name") or "",
            "ic": flight.get("airline_icao") or "",
            "fr": flight.get("origin") or "",
            "to": flight.get("destination") or "",
            "ct": flight.get("destination_city") or "",
            "av": flight.get("aircraft") or "",
            "lv": flight.get("level") or "",
            "km": flight.get("distance_km"),
        }
    if ecran:
        # Le firmware minute ses annonces lui-meme et ne connait que les
        # ecrans de fond : lui envoyer "alerte_meteo" le ferait retomber sur
        # l'ecran de veille, faute de savoir quoi en faire.
        payload["sc"] = ECRAN_DE_FOND.get(ecran, ecran)
    if prieres:
        jour = prieres.get("jour") or []
        payload["pr"] = {
            "n": prieres.get("nom") or "",
            "a": prieres.get("adhan") or "",
            "i": prieres.get("iqama") or "",
            "r": prieres.get("restant") or "",
            "m": prieres.get("mosquee") or "",
            "h": prieres.get("heure") or "",
            "u": bool(prieres.get("prise_main")),
            "e": prieres.get("phase") == "encours",
            "d": bool(prieres.get("demain")),
            # Les cinq horaires en une seule chaine : les noms etant fixes des
            # deux cotes, les transmettre aurait double la taille pour rien.
            "pt": ",".join(p.get("adhan") or "" for p in jour[:5]),
            "rg": prieres.get("rang", -1),
            # Les titres en une seule chaine, separes par une barre : meme
            # economie que pour les horaires.
            "an": SEP_ANNONCES.join(prieres.get("annonces") or ()),
            "jm": any((p.get("nom") or "").startswith("JOU") for p in jour),
        }
    if meteo:
        # L'icone voyage en rang et non en nom : les sept silhouettes sont
        # fixes des deux cotes, un entier suffit a les designer.
        try:
            rang = icones_meteo.ORDRE.index(meteo.get("icone"))
        except ValueError:
            rang = -1
        payload["mt"] = {
            "t": meteo.get("temperature"),
            "r": meteo.get("ressenti"),
            "v": meteo.get("vent_kmh"),
            "i": rang,
            "x": meteo.get("texte") or "",
            "l": meteo.get("lieu") or "",
            "pm": -1 if meteo.get("pluie_min") is None
                  else meteo["pluie_min"],
            "ph": meteo.get("pluie_heure") or "",
            "h": meteo.get("heure") or "",
        }
    if heure:
        payload["hr"] = {"h": heure.get("heure") or "",
                         "d": heure.get("date") or ""}
        if heure.get("luminosite") is not None:
            payload["br"] = heure["luminosite"]
    if rang_adkar is not None:
        # Un entier suffit : les entrees sont les memes des deux cotes, et
        # dans le meme ordre, puisque le meme script les a generees.
        payload["ad"] = rang_adkar
    if son:
        # Le volume part meme sans rien a jouer : le DFPlayer le retient
        # d'une piste a l'autre, et le regler au moment de jouer serait tard.
        payload["au"] = {"s": son.get("son", 0),
                         "c": son.get("cue") or "",
                         "v": son.get("volume", -1)}
    if usage:
        # Les comptes a rebours partent tout faits : l'ESP32 n'a pas
        # d'horloge, il ne saurait pas les recalculer.
        payload["cl"] = {
            "ka": usage.get("cle_a") or "",
            "ra": -1 if usage.get("restant_a") is None else usage["restant_a"],
            "ta": usage.get("reset_a") or "",
            "kb": usage.get("cle_b") or "",
            "rb": -1 if usage.get("restant_b") is None else usage["restant_b"],
            "tb": usage.get("reset_b") or "",
        }
    return payload


def _dessinateur(ecran, donnees, elapsed, logo_dir, avancement=1.0):
    """Fonction qui dessine un ecran donne dans un cadre fourni."""
    flight, prieres, meteo, heure, rang_adkar, usage = donnees

    def dessine(frame):
        if ecran == "heure":
            ecran_heure.render(heure, frame=frame)
        elif ecran == "alerte":
            ecran_alerte.render(flight, avancement, frame=frame)
        elif ecran == "alerte_priere":
            ecran_alerte.render_priere(prieres, avancement, frame=frame)
        elif ecran == "alerte_meteo":
            ecran_meteo.render_annonce(meteo, avancement, frame=frame)
        elif ecran == "priere":
            ecran_prieres.render(prieres, frame=frame)
        elif ecran == "horaires":
            ecran_horaires.render(prieres, elapsed, frame=frame)
        elif ecran == "annonces":
            ecran_annonces.render(prieres, elapsed, frame=frame)
        elif ecran == "meteo":
            ecran_meteo.render(meteo, frame=frame)
        elif ecran == "claude":
            ecran_claude.render(usage, elapsed,
                                heure=(heure or {}).get("heure"), frame=frame)
        elif ecran == "adkar":
            ecran_adkar.render(rang_adkar, elapsed,
                               heure=(heure or {}).get("heure"), frame=frame)
        elif ecran == "vol":
            panel.render(flight, elapsed, logo_dir, frame=frame,
                         heure=(heure or {}).get("heure"))
        else:
            panel.render(None, frame=frame,
                         heure=(heure or {}).get("heure"))
    return dessine


def render_screen(gateway, config, elapsed):
    """Image courante du panneau, alerte et transition comprises."""
    etat = gateway.screen_transition()
    logo_dir = os.path.join(HERE, config.get("logo_dir", "logos"))
    ecran = etat["ecran"]
    donnees = (etat["flight"], etat["prieres"], etat["meteo"], etat["heure"],
               etat["adkar"], etat["usage"])

    def avance(nom):
        if nom == "alerte_priere":
            return gateway.avancement_alerte_priere()
        if nom == "alerte_meteo":
            return gateway.avancement_alerte_meteo()
        return gateway.avancement_alerte()

    entrant = _dessinateur(ecran, donnees, elapsed, logo_dir, avance(ecran))

    if etat["precedent"] != ecran and transitions.en_cours(etat["depuis_ms"]):
        sortant = _dessinateur(etat["precedent"], etat["donnees_precedentes"],
                               elapsed, logo_dir, avance(etat["precedent"]))
        frame = transitions.compose(sortant, entrant,
                                    transitions.avancement(etat["depuis_ms"]))
    else:
        frame = panel.Frame()
        entrant(frame)

    # La luminosite s'applique apres coup, comme le ferait le panneau : elle
    # ne change pas la mise en page, seulement son intensite.
    frame.attenue(gateway.luminosite_relative())
    return frame, ecran, donnees


