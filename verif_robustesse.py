"""Robustesse de la passerelle : delais stricts, fils isoles, caches surs.

    python3 verif_robustesse.py

Un petit serveur HTTP local joue les APIs malades (lente, muette, trop
bavarde, en erreur) : aucun acces a Internet n'est necessaire. Appele aussi
par test_hors_ligne.py.
"""

import datetime
import json
import os
import sys
import tempfile
import threading
import time
import unittest.mock
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import collecteur
import flightsource
import meteosource
import passerelle
import prieresource
import stockage
import telechargement


class _Malade(BaseHTTPRequestHandler):
    """Les pannes d'API qu'on rencontre en vrai, a la demande."""

    def log_message(self, *args):
        pass

    def _entete(self, taille=None):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        if taille is not None:
            self.send_header("Content-Length", str(taille))
        self.end_headers()

    def do_GET(self):
        chemin = self.path.split("?")[0]
        try:
            if chemin == "/ok":
                corps = b'{"ok": true}'
                self._entete(len(corps))
                self.wfile.write(corps)
            elif chemin == "/lent":
                # un octet toutes les 0,2 s : chaque lecture respecte le
                # timeout d'urllib, la requete entiere ne finit jamais
                self._entete(1000)
                for _ in range(1000):
                    self.wfile.write(b" ")
                    self.wfile.flush()
                    time.sleep(0.2)
            elif chemin == "/muet":
                self._entete(10)
                self.wfile.flush()
                time.sleep(5)
            elif chemin == "/gros":
                self._entete()
                bloc = b"x" * 65536
                for _ in range(100):
                    self.wfile.write(bloc)
            else:
                self.send_error(404)
        except (BrokenPipeError, ConnectionResetError):
            pass


def _serveur():
    serveur = ThreadingHTTPServer(("127.0.0.1", 0), _Malade)
    serveur.daemon_threads = True
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    return serveur, "http://127.0.0.1:%d" % serveur.server_address[1]


def _chrono(fonction):
    """(resultat ou exception, secondes)"""
    debut = time.monotonic()
    try:
        resultat = fonction()
    except Exception as exc:
        resultat = exc
    return resultat, time.monotonic() - debut


def _telechargement(check, base):
    ok, _ = _chrono(lambda: telechargement.lire(base + "/ok", 2))
    check("http : une reponse normale arrive entiere", ok == b'{"ok": true}')
    for chemin in ("/lent", "/muet"):
        res, duree = _chrono(lambda: telechargement.lire(base + chemin, 1.0))
        check("http : %s abandonne a l'echeance, pas au-dela" % chemin,
              isinstance(res, telechargement.DelaiDepasse) and duree < 1.6,
              "%s en %.2f s" % (type(res).__name__, duree))
    res, _ = _chrono(lambda: telechargement.lire(base + "/gros", 5,
                                                 taille_max=1024 * 1024))
    check("http : une reponse demesuree est coupee",
          isinstance(res, telechargement.TropVolumineux),
          type(res).__name__)
    res, _ = _chrono(lambda: telechargement.lire(base + "/absent", 2))
    check("http : une erreur HTTP reste une URLError",
          isinstance(res, urllib.error.HTTPError), type(res).__name__)
    res, _ = _chrono(lambda: telechargement.lire("http://127.0.0.1:9/", 2))
    check("http : un refus de connexion est une URLError",
          isinstance(res, urllib.error.URLError), type(res).__name__)

    # Plafond de 5 s : meme un appelant qui demande une minute est coupe
    with unittest.mock.patch.object(telechargement, "DELAI_MAX", 0.5):
        res, duree = _chrono(lambda: telechargement.lire(base + "/muet", 60))
    check("http : aucune requete ne depasse DELAI_MAX, quoi qu'on demande",
          isinstance(res, telechargement.DelaiDepasse) and duree < 0.9,
          "%.2f s pour 60 demandees" % duree)
    check("http : DELAI_MAX vaut au plus 5 s", telechargement.DELAI_MAX <= 5)
    delais = {}

    def espion(nom):
        def lire(url, delai=telechargement.DELAI_MAX, *args, **kwargs):
            delais[nom] = delai
            raise telechargement.DelaiDepasse("espion")
        return lire
    for nom, appel in (
            ("vols", lambda: flightsource._get_json("http://x/")),
            ("prieres", lambda: prieresource.fetch_conf("essai")),
            ("meteo", lambda: meteosource.fetch(48.8, 2.3))):
        with unittest.mock.patch.object(telechargement, "lire_texte",
                                        espion(nom)):
            _chrono(appel)
    check("http : les trois sources demandent 5 s au plus",
          len(delais) == 3 and max(delais.values()) <= 5,
          ", ".join("%s %.0f s" % kv for kv in sorted(delais.items())))

    # Une route en retard ne doit plus faire tomber tout le sondage : le
    # TimeoutError brut traversait les except de lookup_route.
    cache = flightsource.RouteCache(os.devnull)
    with unittest.mock.patch.object(flightsource, "DELAI_S", 0.5), \
            unittest.mock.patch.object(flightsource, "ADSBDB_CALLSIGN",
                                       base + "/muet?%s"), \
            unittest.mock.patch.object(flightsource, "HEXDB_ROUTE",
                                       base + "/muet?%s"):
        res, duree = _chrono(lambda: flightsource.lookup_route("AFR1", cache))
    check("http : une route muette donne une route vide, pas une exception",
          res == {} and duree < 2.0, "%r en %.2f s" % (res, duree))


def _collecteurs(check):
    rapports = []

    def rapporte(nom, erreur, duree):
        rapports.append((nom, erreur))

    etats = iter([RuntimeError("imprevu"), "api en panne", None])

    def etape():
        etat = next(etats)
        if isinstance(etat, Exception):
            raise etat
        return etat

    c = collecteur.Collecteur("essai", etape, 10, rapporte, periode_max=30)
    attentes = [c.tour() for _ in range(3)]
    check("collecte : une exception imprevue ne tue pas le collecteur",
          len(rapports) == 3 and isinstance(rapports[0][1], RuntimeError))
    check("collecte : les echecs espacent les essais, plafonnes",
          attentes[0] > 19 and 29 < attentes[1] <= 30,
          "%.1f s puis %.1f s" % tuple(attentes[:2]))
    check("collecte : un succes retablit la periode normale",
          9 < attentes[2] <= 10 and c.echecs == 0, "%.1f s" % attentes[2])

    # Une source lente ne retarde pas les autres : chacune a son fil
    arret = threading.Event()
    tours = {"lente": 0, "rapide": 0}

    def compte(nom, pause):
        def etape():
            tours[nom] += 1
            time.sleep(pause)
        return etape
    for nom, pause, periode in (("lente", 3.0, 1), ("rapide", 0, 0.05)):
        collecteur.Collecteur(nom, compte(nom, pause), periode,
                              rapporte).demarre(arret)
    time.sleep(0.6)
    arret.set()
    check("collecte : une source bloquee ne retarde pas les autres",
          tours["lente"] == 1 and tours["rapide"] >= 5,
          "lente %d tour, rapide %d tours" % (tours["lente"],
                                              tours["rapide"]))


def _derniere_valeur(check):
    g = passerelle.Gateway({"latitude": 48.85, "longitude": 2.35,
                            "mosquee_slug": "essai"})
    g.journal = lambda ligne: None
    g.meteo = {"temperature": 18, "icone": "nuage"}
    panne = urllib.error.URLError("open-meteo injoignable")

    def meteo_en_panne(config, cache, erreurs=None):
        erreurs.append(panne)
        return None
    with unittest.mock.patch.object(meteosource, "charge", meteo_en_panne):
        erreur = g._meteo_step()
    g.rapporte("meteo", erreur, 0.1)
    check("derniere valeur : la meteo connue reste servie pendant la panne",
          g.current_meteo() == {"temperature": 18, "icone": "nuage"})
    etat = g.status()["sources"]["meteo"]
    check("derniere valeur : la panne meteo est visible dans l'etat",
          etat["ok"] is False and "injoignable" in etat["erreur"]
          and etat["echecs"] == 1, etat["erreur"])

    # Pendant la panne, les essais s'espacent jusqu'a dix minutes : l'heure
    # et le decompte de pluie de l'ecran meteo ne doivent pas se figer.
    g.meteo_brut = {"temperature_2m": 18.2, "weather_code": 61, "is_day": 1,
                    "_quarts": {"time": ["2026-09-24T17:30"],
                                "precipitation": [1.0]}}
    avant = g.current_meteo(datetime.datetime(2026, 9, 24, 17, 0))
    apres = g.current_meteo(datetime.datetime(2026, 9, 24, 17, 10))
    check("derniere valeur : l'heure meteo avance sans nouveau sondage",
          avant["heure"] == "17:00" and apres["heure"] == "17:10",
          "%s puis %s" % (avant["heure"], apres["heure"]))
    g.meteo_brut = None

    g.conf = {"deja": "connu"}
    with unittest.mock.patch.object(prieresource, "fetch_conf",
                                    side_effect=panne):
        g.prieres_cache = prieresource.PrayerCache(
            os.path.join(tempfile.mkdtemp(), "vide.json"))
        erreur = g._prieres_step()
    check("derniere valeur : le confData en memoire survit a Mawaqit en panne",
          g.conf == {"deja": "connu"} and erreur is panne)

    # Cache perime + reseau en panne : l'ecran reste, l'erreur remonte
    with tempfile.TemporaryDirectory() as dossier:
        cache = prieresource.PrayerCache(os.path.join(dossier, "p.json"))
        cache.data["essai"] = {"ts": 0, "conf": {"perime": True}}
        erreurs = []
        with unittest.mock.patch.object(prieresource, "fetch_conf",
                                        side_effect=panne):
            conf = prieresource.load_conf("essai", cache, erreurs)
    check("derniere valeur : cache perime servi, et l'echec rapporte",
          conf == {"perime": True} and erreurs == [panne])

    with unittest.mock.patch.object(flightsource, "poll",
                                    side_effect=panne):
        g.flight = {"callsign": "AFR1"}
        g.last_seen = time.time()
        erreur = g._live_step()
    check("derniere valeur : l'avion connu reste pendant une panne adsb.lol",
          g.current() == {"callsign": "AFR1"} and erreur is panne)


def _observabilite(check):
    g = passerelle.Gateway({})
    lignes = []
    g.journal = lignes.append
    panne = urllib.error.URLError("adsb.lol injoignable")
    g.rapporte("vols", None, 0.1)
    for _ in range(3):
        g.rapporte("vols", panne, 5.0)
    g.rapporte("vols", None, 0.2)
    check("console : une ligne a l'entree en panne, une au retablissement",
          len(lignes) == 2 and "EN PANNE" in lignes[0]
          and "derniere valeur connue du" in lignes[0]
          and "retablie apres 3" in lignes[1], " | ".join(lignes))
    g.rapporte("vols", panne, 5.0)
    succes = g.sources["vols"]["dernier_succes"]
    etat = g.status(maintenant=succes + 125)["sources"]["vols"]
    check("etat : l'age de la derniere donnee reussie est expose",
          etat["age_s"] == 125 and etat["ok"] is False, str(etat["age_s"]))
    g2 = passerelle.Gateway({})
    g2.journal = lignes.append
    g2.rapporte("meteo", panne, 5.0)
    check("etat : une source jamais reussie n'a pas d'age",
          g2.status()["sources"]["meteo"]["age_s"] is None
          and "aucune" in lignes[-1], lignes[-1])


def _caches(check):
    with tempfile.TemporaryDirectory() as dossier:
        chemin = os.path.join(dossier, "routes.json")
        maintenant = time.time()
        with open(chemin, "w", encoding="utf-8") as handle:
            json.dump({"VIEUX": {"ts": maintenant - 13 * 3600, "route": {}},
                       "FRAIS": {"ts": maintenant, "route": {"o": "CDG"}},
                       "CASSE": "pas un dict"}, handle)
        cache = flightsource.RouteCache(chemin)
        check("cache des routes : les entrees perimees partent au chargement",
              set(cache.data) == {"FRAIS"}, ", ".join(sorted(cache.data)))
        cache.data["VIEUX2"] = {"ts": maintenant - 13 * 3600, "route": {}}
        cache.put("NEUF", {"o": "ORY"})
        relu = stockage.lit_json(chemin)
        check("cache des routes : purge a chaque ajout, fichier relisible",
              set(relu) == {"FRAIS", "NEUF"}, ", ".join(sorted(relu)))

        # Un echec au moment de substituer le fichier le laisse intact
        with unittest.mock.patch.object(os, "replace",
                                        side_effect=OSError("disque plein")):
            ecrit = stockage.ecrit_json_atomique(chemin, {"NOUVEAU": 1})
        restes = [n for n in os.listdir(dossier) if n.endswith(".tmp")]
        check("ecriture atomique : un echec laisse l'ancien fichier intact",
              not ecrit and set(stockage.lit_json(chemin)) == {"FRAIS",
                                                               "NEUF"})
        check("ecriture atomique : aucun fichier provisoire ne traine",
              not restes, ", ".join(restes))

        with open(chemin, "w", encoding="utf-8") as handle:
            handle.write('{"FRAIS": {"ts": ')  # coupe en pleine ecriture
        check("cache des routes : un fichier tronque ne fait pas planter",
              flightsource.RouteCache(chemin).data == {})


def verifie(check):
    serveur, base = _serveur()
    try:
        _telechargement(check, base)
    finally:
        serveur.shutdown()
    _collecteurs(check)
    _derniere_valeur(check)
    _observabilite(check)
    _caches(check)


def main():
    checks = []
    verifie(lambda l, c, d="": checks.append((l, bool(c), d)))
    for libelle, ok, detail in checks:
        print("%s  %s  %s" % ("OK  " if ok else "ECHEC", libelle, detail))
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
