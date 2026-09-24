"""Passerelle : interroge les sources et decide quel ecran passe a l'antenne.

Un fil de fond sonde les APIs a la cadence de config.json ; les requetes HTTP
lisent l'etat courant sans jamais attendre le reseau.

C'est ici que vit la rotation des ecrans, et les annonces d'arrivee. Le
firmware obeit au resultat, transmis dans le champ "sc" de /flight.

Chaque source a son propre fil de collecte (cf. collecteur.py) : une API
lente ne retarde qu'elle-meme, et son dernier etat connu reste servi.
"""

import datetime
import os
import threading
import time

import adkar
import audio
import claudesource
import collecteur
import ecran_annonces
import ecran_adkar
import ecran_alerte
import ecran_heure
import flightsource
import horaires
import meteosource
import panel
import prieresource

HERE = os.path.dirname(os.path.abspath(__file__))

# Ecrans qu'un avion qui arrive ne doit pas interrompre.
ECRANS_PRIERE = ("priere", "horaires")

DEMO_FLIGHTS = [
    {"callsign": "AFR1234", "airline_name": "Air France", "airline_icao": "AFR",
     "origin": "CDG", "destination": "JFK", "destination_city": "New York",
     "level": "FL340", "altitude_ft": 34000, "distance_km": 4.2},
    {"callsign": "EZY83QK", "airline_name": "Easyjet", "airline_icao": "EZY",
     "origin": "ORY", "destination": "LIS", "destination_city": "Lisbonne",
     "level": "FL280", "altitude_ft": 28000, "distance_km": 8.7},
    {"callsign": "UAE76", "airline_name": "Emirates", "airline_icao": "UAE",
     "origin": "DXB", "destination": "LHR", "destination_city": "Londres",
     "level": "FL390", "altitude_ft": 39000, "distance_km": 11.3},
]

# Priere fictive du mode demo : aucun appel reseau, mise en page verifiable
# le soir ou hors couverture, comme les vols ci-dessus.
DEMO_PRIERE = {
    "nom": "MAGHREB", "adhan": "19:59", "iqama": "20:09", "phase": "adhan",
    "restant_min": 12, "restant": "12 MIN", "chourouk": "07:33",
    "prise_main": False, "demain": False, "mosquee": "MOSQUEE",
    # la journee complete, sans quoi l'ecran des horaires serait saute
    "jour": [{"nom": nom, "adhan": heure} for nom, heure in
             zip(("FAJR", "DOHR", "ASR", "MAGHREB", "ICHA"),
                 ("05:54", "13:45", "17:09", "19:59", "21:22"))],
    "rang": 3,
}

# Meteo fictive du mode demo : sans elle, l'ecran meteo et son annonce
# seraient absents de la rotation des qu'on travaille hors ligne.
DEMO_METEO = {
    "temperature": 18, "ressenti": 16, "vent_kmh": 12, "code": 3,
    "texte": "COUVERT", "icone": "nuage", "jour": True, "lieu": "PARIS",
}


class Gateway:
    """Interroge les APIs en tache de fond et garde le dernier vol connu."""

    def __init__(self, config):
        self.config = config
        self.cache = flightsource.RouteCache(os.path.join(HERE, flightsource.CACHE_FILE))
        self.prieres_cache = prieresource.PrayerCache(
            os.path.join(HERE, prieresource.CACHE_FILE))
        self.meteo_cache = meteosource.MeteoCache(
            os.path.join(HERE, meteosource.CACHE_FILE))
        # Reentrant : _rotation le tient en appelant duree_ecran, qui peut
        # relire current_prieres et le reprendre. Un verrou simple bloquait
        # la passerelle pour de bon, cf. test 22l.
        self.lock = threading.RLock()
        self.flight = None
        # Le confData de la mosquee, garde tel quel : la priere courante s'en
        # deduit a chaque demande, cf. current_prieres.
        self.conf = None
        self.prieres = None
        self.meteo = None
        # donnees brutes d'Open-Meteo : la meteo affichee s'en deduit a
        # chaque demande, cf. current_meteo
        self.meteo_brut = None
        self.usage = None
        self.last_seen = 0.0
        self.last_poll = 0.0
        self.source = "demarrage"
        self.error = None
        self.started = time.time()
        self._demo_index = 0
        # suivi des bascules d'ecran, pour animer la transition
        self.ecran = "veille"
        self.ecran_precedent = "veille"
        self.donnees = (None, None, None, None, None, None)
        self.donnees_precedentes = (None, None, None, None, None, None)
        self.bascule = 0.0
        # annonces : ce qui a deja ete annonce, et le debut de l'animation
        self.callsign_annonce = None
        self.alerte = 0.0
        self.priere_annoncee = None
        self.alerte_priere = 0.0
        self.alerte_meteo = 0.0
        # rotation des ecrans
        self.rotation_ecran = None
        self.rotation_debut = 0.0
        # sante de chaque source, cf. rapporte() ; et l'arret des collecteurs
        self.sources = {}
        self.arret = threading.Event()
        self.collecteurs = []

    def current(self):
        with self.lock:
            if self.flight is None:
                return None
            age = time.time() - self.last_seen
            if age > self.config.get("hold_seconds", 90):
                return None
            return dict(self.flight)

    def current_prieres(self, now=None):
        """Priere courante, recalculee maintenant et non au dernier sondage.

        L'adhan doit retentir a l'heure de la mosquee, pas jusqu'a douze
        secondes plus tard : le calcul est pur et instantane, on le refait
        plutot que de servir un instantane vieux d'un tour de boucle. Le
        reseau, lui, reste a la cadence de _prieres_step.
        """
        with self.lock:
            conf = self.conf
            secours = dict(self.prieres) if self.prieres else None
        if not conf:
            return secours
        try:
            frais = prieresource.depuis_conf(
                conf, self.config, self.config.get("mosquee_slug"), now)
        except Exception:
            return secours
        return frais or secours

    def current_meteo(self, now=None):
        """Meteo mise en forme maintenant, comme current_prieres.

        L'heure et le decompte de pluie ne vieillissent pas avec le dernier
        sondage. Le mode demo, sans donnees brutes, sert self.meteo tel quel.
        """
        with self.lock:
            brut = self.meteo_brut
            secours = dict(self.meteo) if self.meteo else None
        if not brut:
            return secours
        try:
            return meteosource.depuis_brut(brut, self.config, now) or secours
        except Exception:
            return secours

    def current_usage(self):
        """Quota Claude Code, recalcule a chaque lecture.

        Les comptes a rebours dependent de l'heure qu'il est, pas de l'heure
        du dernier sondage : on relit donc le fichier plutot que de garder
        un etat qui vieillirait mal.
        """
        try:
            return claudesource.poll(self.config)
        except Exception:
            return None

    def _minute(self, valeur, defaut):
        """Borne de la plage nocturne -> minutes depuis minuit.

        Accepte une heure pleine (22), une heure precise ("23:30"), ou le mot
        "fajr" qui suit la premiere priere du jour : la nuit se termine quand
        la mosquee appelle, pas a une heure fixe qui derive avec les saisons.
        """
        if isinstance(valeur, str) and valeur.strip().lower() == "fajr":
            prieres = self.current_prieres() or {}
            jour = prieres.get("jour") or []
            if jour:
                minutes = horaires._minutes(jour[0].get("adhan"))
                if minutes is not None:
                    return minutes
            return defaut * 60  # horaires indisponibles : on retombe sur l'heure
        if isinstance(valeur, str):
            minutes = horaires._minutes(valeur)
            return minutes if minutes is not None else defaut * 60
        try:
            return int(valeur) * 60
        except (TypeError, ValueError):
            return defaut * 60

    def de_nuit(self, now=None):
        """Vrai pendant la plage nocturne, qui peut traverser minuit.

        Une seule definition de la nuit pour tout le panneau : la luminosite
        et le volume la partagent, et un panneau qui s'assombrit la nuit tout
        en hurlant l'adhan n'aurait aucun sens.
        """
        debut = self._minute(self.config.get("nuit_debut", 23), 23)
        fin = self._minute(self.config.get("nuit_fin", "fajr"), 7)
        if debut == fin:
            return False
        quand = now or datetime.datetime.now()
        maintenant = quand.hour * 60 + quand.minute
        return (maintenant >= debut or maintenant < fin) if debut > fin \
            else (debut <= maintenant < fin)

    def luminosite(self, now=None):
        """Luminosite du panneau selon l'heure, de 0 a 255.

        Un panneau a pleine puissance dans un salon a trois heures du matin
        est insupportable. Mettre luminosite_nuit a 0 eteint le panneau
        plutot que de le tamiser.
        """
        return self.config.get("luminosite_nuit", 8) if self.de_nuit(now) \
            else self.config.get("luminosite_jour", 40)

    def current_audio(self, now=None):
        """Son a jouer, volume, et cle d'unicite. Cf. audio.py."""
        return audio.etat(self.current_prieres(), self.config,
                          self.de_nuit(now))

    def luminosite_relative(self, now=None):
        """Attenuation a appliquer a l'image du simulateur, de 0 a 255.

        Le niveau envoye a l'ESP32 est un rapport cyclique : 40 sur 255 donne
        un panneau LED confortable, parce qu'a fond il eblouit. Appliquer ce
        meme 40 aux pixels d'un moniteur donnerait une image a 16 %, illisible
        en plein jour. Le simulateur montre donc la baisse *relative* : plein
        eclat le jour, et le meme rapport nuit/jour que le vrai panneau la
        nuit venue.
        """
        jour = self.config.get("luminosite_jour", 40) or 1
        courante = self.luminosite(now)
        return max(0, min(255, int(round(255.0 * courante / jour))))

    def current_adkar(self, now=None):
        """Rang du nom d'Allah du jour.

        Deduit de la date et de rien d'autre : pas d'etat a garder, pas de
        derive possible entre la passerelle et le panneau, et le meme nom
        toute la journee, qu'on redemarre le serveur ou non. Un nom par jour
        laisse le temps de le retenir ; les 99 font un cycle de trois mois.

        C'est la passerelle qui le transmet, comme elle transmet l'ecran,
        pour que les deux moities du jumeau montrent toujours le meme nom.
        """
        combien = adkar.combien()
        if not combien:
            return None
        quand = now or datetime.datetime.now()
        return quand.toordinal() % combien

    def duree_adkar(self, now=None):
        """Duree de l'ecran adkar, jamais moins qu'un tour de sa ligne.

        La signification defile sur plusieurs centaines de pixels. Quitter
        l'ecran avant la fin du tour montrerait une phrase coupee en deux,
        ce qui ne sert a personne ; on allonge donc le tour s'il le faut.
        """
        durees = self.config.get("duree_ecrans") or {}
        try:
            plancher = float(durees.get("adkar",
                                        self.config.get("rotation_seconds",
                                                        30)))
        except (TypeError, ValueError):
            plancher = self.config.get("rotation_seconds", 30)
        rang = self.current_adkar(now)
        if rang is None:
            return plancher
        tour = ecran_adkar.duree_defilement(adkar.entree(rang))
        return max(plancher, tour + 2.0)

    def current_heure(self, now=None):
        """Heure et date du jour, calculees ici : l'ESP32 n'a pas d'horloge."""
        quand = now or datetime.datetime.now()
        return {"heure": quand.strftime("%H:%M"),
                "date": ecran_heure.format_date(quand),
                "luminosite": self.luminosite(quand)}

    def screen(self):
        """Arbitre entre les deux ecrans.

        La priere passe devant l'avion quand le panneau prend la main, c'est
        a dire autour de l'adhan et jusqu'a l'iqama. Le reste du temps l'avion
        gagne, et les horaires occupent l'ecran de veille.
        """
        flight = self.current()
        prieres = self.current_prieres()
        meteo = self.current_meteo()
        heure = self.current_heure()
        rang_adkar = self.current_adkar()
        usage = self.current_usage()

        # La priere qui prend la main passe avant tout le reste
        if prieres and prieres.get("prise_main"):
            return ("alerte_priere" if self._alerte_priere_en_cours(prieres)
                    else "priere", flight, prieres, meteo, heure, rang_adkar,
                    usage)

        # Un avion qui vient d'arriver s'annonce et garde l'ecran un tour,
        # mais il ne coupe jamais un ecran de priere : sur une horloge murale,
        # l'heure de la priere passe avant l'avion qui traverse. L'annonce
        # n'est pas perdue, elle attend que la rotation quitte ces ecrans.
        if flight and self.rotation_ecran not in ECRANS_PRIERE \
                and self._alerte_en_cours(flight):
            return ("alerte", flight, prieres, meteo, heure, rang_adkar,
                    usage)

        ecran = self._rotation(flight, prieres, meteo, rang_adkar, usage)

        # La meteo s'annonce a l'arrivee de son tour, et non sur un changement
        # de donnee : le temps qu'il fait n'arrive pas, il est deja la.
        if ecran == "meteo" and self._alerte_meteo_en_cours():
            ecran = "alerte_meteo"
        return ecran, flight, prieres, meteo, heure, rang_adkar, usage

    def duree_ecran(self, ecran, prieres=None):
        """Combien de temps un ecran reste a l'antenne, en secondes.

        Une duree unique conviendrait mal : le bandeau des horaires met une
        quarantaine de secondes a faire un tour complet, tandis que l'heure se
        lit d'un coup d'oeil. Sur un panneau accroche au mur, trop rapide
        fatigue et trop lent donne l'impression d'un ecran fige.
        """
        durees = self.config.get("duree_ecrans") or {}
        defaut = self.config.get("rotation_seconds", 30)
        if ecran == "adkar":
            return self.duree_adkar()
        if ecran == "annonces":
            return self.duree_annonces(prieres)
        try:
            return float(durees.get(ecran, defaut))
        except (TypeError, ValueError):
            return defaut

    def duree_annonces(self, prieres=None):
        """Duree de l'ecran des annonces, au moins un tour de bandeau.

        Meme raison que pour les adkar : une annonce coupee en deux ne dit
        rien, et leur nombre change au gre de la mosquee.

        prieres est passe par _rotation quand il l'a deja sous la main :
        inutile de le recalculer. Sinon on le relit, ce que le verrou
        reentrant permet meme depuis _rotation.
        """
        durees = self.config.get("duree_ecrans") or {}
        try:
            plancher = float(durees.get("annonces",
                                        self.config.get("rotation_seconds",
                                                        30)))
        except (TypeError, ValueError):
            plancher = self.config.get("rotation_seconds", 30)
        if prieres is None:
            prieres = self.current_prieres()
        titres = (prieres or {}).get("annonces") or ()
        if not titres:
            return plancher
        return max(plancher, ecran_annonces.duree_tour(titres) + 2.0)

    def _rotation(self, flight, prieres, meteo, rang_adkar=None,
                  usage=None):
        """Ecran courant de la rotation, qui avance toutes les N secondes.

        Les ecrans indisponibles sont sautes : pas d'avion, pas d'ecran de
        vol. La liste peut donc changer de taille d'un tour a l'autre.
        """
        disponibles = []
        if flight:
            disponibles.append("vol")
        if prieres:
            disponibles.append("priere")
            if prieres.get("jour"):
                disponibles.append("horaires")
            # pas d'annonce publiee, pas d'ecran : la mosquee decide
            if prieres.get("annonces"):
                disponibles.append("annonces")
        if meteo:
            disponibles.append("meteo")
        if rang_adkar is not None:
            disponibles.append("adkar")
        # l'ecran Claude Code ne parait que si le releve est frais, cf.
        # claudesource.poll : mieux vaut un ecran en moins qu'un chiffre faux
        if usage:
            disponibles.append("claude")
        # l'heure est toujours disponible, elle ne depend d'aucune source
        disponibles.append("heure")

        with self.lock:
            expire = (time.time() - self.rotation_debut
                      >= self.duree_ecran(self.rotation_ecran, prieres))
            if self.rotation_ecran in disponibles and not expire:
                return self.rotation_ecran
            if self.rotation_ecran in disponibles:
                rang = disponibles.index(self.rotation_ecran) + 1
                suivant = disponibles[rang % len(disponibles)]
            else:
                # l'ecran courant a disparu de la liste : on repart du debut
                suivant = disponibles[0]
            if suivant == "meteo":
                self.alerte_meteo = time.time()
            self.rotation_ecran = suivant
            self.rotation_debut = time.time()
            return suivant

    def _alerte_en_cours(self, flight):
        """Vrai pendant les premieres secondes d'un vol qu'on n'a pas annonce.

        Meme regle que dans le firmware : c'est le changement d'indicatif qui
        declenche l'annonce, pas la passerelle. L'ESP32 n'interroge celle-ci
        que toutes les douze secondes et manquerait la fenetre.
        """
        callsign = flight.get("callsign") or ""
        with self.lock:
            if callsign != self.callsign_annonce:
                self.callsign_annonce = callsign
                self.alerte = time.time()
                # apres l'annonce, l'avion garde l'ecran un tour complet
                self.rotation_ecran = "vol"
                self.rotation_debut = time.time()
            return (time.time() - self.alerte) * 1000.0 < ecran_alerte.ALERTE_MS

    def _alerte_priere_en_cours(self, prieres):
        """Vrai pendant les premieres secondes d'une priere qui prend la main.

        Meme regle que dans le firmware : c'est le nom de la priere qui
        declenche l'annonce, une fois par priere.
        """
        nom = prieres.get("nom") or ""
        with self.lock:
            if nom != self.priere_annoncee:
                self.priere_annoncee = nom
                self.alerte_priere = time.time()
            ecoule = (time.time() - self.alerte_priere) * 1000.0
            return ecoule < ecran_alerte.ALERTE_MS

    def _duree_annonce_meteo(self):
        """Duree de l'annonce, jamais plus de la moitie d'un tour.

        Sans ce plafond, un rotation_seconds plus court que l'annonce ferait
        disparaitre l'ecran meteo : le tour se terminerait avant que l'icone
        ait fini de se poser, et on ne verrait jamais la temperature.
        """
        moitie = self.config.get("rotation_seconds", 30) * 500.0
        return min(ecran_alerte.ALERTE_MS, moitie)

    def _alerte_meteo_en_cours(self):
        """Vrai pendant les premieres secondes du tour de la meteo."""
        with self.lock:
            if not self.alerte_meteo:
                return False
            ecoule = (time.time() - self.alerte_meteo) * 1000.0
            return ecoule < self._duree_annonce_meteo()

    def avancement_alerte_meteo(self):
        """Position dans l'animation d'annonce meteo, entre 0.0 et 1.0."""
        with self.lock:
            if not self.alerte_meteo:
                return 1.0
            ecoule = (time.time() - self.alerte_meteo) * 1000.0
            return min(1.0, ecoule / self._duree_annonce_meteo())

    def _avancement(self, depart):
        if not depart:
            return 1.0
        ecoule = (time.time() - depart) * 1000.0
        return min(1.0, ecoule / float(ecran_alerte.ALERTE_MS))

    def avancement_alerte(self):
        """Position dans l'animation d'annonce d'avion, entre 0.0 et 1.0."""
        with self.lock:
            return self._avancement(self.alerte)

    def avancement_alerte_priere(self):
        """Position dans l'animation d'annonce de priere, entre 0.0 et 1.0."""
        with self.lock:
            return self._avancement(self.alerte_priere)

    def screen_transition(self):
        """Ecran courant, ecran sortant, et ou en est l'animation.

        Les donnees de l'ecran sortant sont figees au moment de la bascule :
        quand on quitte l'ecran vol parce que l'avion a disparu, il faut
        encore pouvoir le dessiner pendant qu'il sort du cadre.
        """
        ecran, flight, prieres, meteo, heure, rang_adkar, usage = \
            self.screen()
        with self.lock:
            if ecran != self.ecran:
                self.ecran_precedent = self.ecran
                self.donnees_precedentes = self.donnees
                self.bascule = time.time()
                self.ecran = ecran
            self.donnees = (flight, prieres, meteo, heure, rang_adkar,
                            usage)
            depuis_ms = (time.time() - self.bascule) * 1000.0 if self.bascule else -1
            return {
                "ecran": ecran, "flight": flight, "prieres": prieres,
                "meteo": meteo, "heure": heure, "adkar": rang_adkar,
                "usage": usage,
                "precedent": self.ecran_precedent,
                "donnees_precedentes": self.donnees_precedentes,
                "depuis_ms": depuis_ms,
            }

    def status(self):
        with self.lock:
            return {"source": self.source, "error": self.error,
                    "last_poll": self.last_poll, "last_seen": self.last_seen,
                    "sources": {nom: dict(etat)
                                for nom, etat in self.sources.items()}}

    def rapporte(self, nom, erreur, duree):
        """Sante d'une source apres chaque tour de son collecteur.

        Une panne ne se tait plus : elle est gardee ici avec son heure, et
        affichee par le simulateur, pendant que la derniere valeur connue
        continue d'etre servie.
        """
        maintenant = time.time()
        with self.lock:
            etat = self.sources.setdefault(nom, {
                "ok": None, "erreur": None, "dernier_succes": None,
                "echecs": 0})
            etat["derniere_tentative"] = maintenant
            etat["duree_ms"] = int(duree * 1000)
            if erreur:
                etat["ok"] = False
                etat["erreur"] = ("%s: %s" % (type(erreur).__name__, erreur)
                                  if isinstance(erreur, BaseException)
                                  else str(erreur))
                etat["echecs"] += 1
            else:
                etat["ok"] = True
                etat["erreur"] = None
                etat["dernier_succes"] = maintenant
                etat["echecs"] = 0

    def _demo_step(self):
        flight = dict(DEMO_FLIGHTS[self._demo_index % len(DEMO_FLIGHTS)])
        self._demo_index += 1
        flight["ticker"] = panel.build_ticker(flight)
        priere = dict(DEMO_PRIERE)
        priere["heure"] = time.strftime("%H:%M")
        meteo = dict(DEMO_METEO)
        meteo["heure"] = priere["heure"]
        with self.lock:
            self.flight = flight
            self.prieres = priere
            self.meteo = meteo
            self.last_seen = time.time()
            self.last_poll = time.time()
            self.source = "demo"
            self.error = None

    def _meteo_step(self):
        """Rafraichit la meteo. Open-Meteo est interroge au quart d'heure au
        plus, le reste du temps c'est une lecture de cache. Renvoie l'erreur
        s'il y en a eu une, cf. collecteur.Collecteur."""
        erreurs = []
        brut = meteosource.charge(self.config, self.meteo_cache, erreurs)
        # sans reponse ni cache, on garde la derniere meteo en memoire
        if brut:
            info = meteosource.depuis_brut(brut, self.config)
            with self.lock:
                self.meteo_brut = brut
                self.meteo = info
        return erreurs[0] if erreurs else None

    def _prieres_step(self):
        """Rafraichit le confData. Le reseau n'est sollicite qu'une fois par
        jour ; la priere courante, elle, se recalcule a chaque demande."""
        slug = self.config.get("mosquee_slug")
        if not slug:
            return None
        erreurs = []
        conf = prieresource.load_conf(slug, self.prieres_cache, erreurs)
        if conf is None:
            # ni reseau ni cache : le dernier confData en memoire reste
            return erreurs[0] if erreurs else "confData introuvable"
        info = prieresource.depuis_conf(conf, self.config, slug)
        with self.lock:
            self.conf = conf
            if info is not None:
                self.prieres = info
        return erreurs[0] if erreurs else None

    def _live_step(self):
        # L'avion a l'ecran, s'il y en a un : il le garde tant qu'aucun autre
        # n'est nettement plus proche, cf. flightsource.pick_overhead.
        actuel = self.current()
        courant = actuel.get("callsign") if actuel else None
        try:
            flight = flightsource.poll(self.config, self.cache, courant)
        except Exception as exc:
            # l'avion deja connu reste affiche jusqu'a hold_seconds
            with self.lock:
                self.last_poll = time.time()
                self.error = "%s: %s" % (type(exc).__name__, exc)
                self.source = "erreur reseau"
            return exc
        with self.lock:
            self.last_poll = time.time()
            self.source = "direct"
            self.error = None
            if flight is not None:
                flight["ticker"] = panel.build_ticker(flight)
                self.flight = flight
                self.last_seen = time.time()
        return None

    def demarre(self):
        """Lance un fil de collecte par source, et rend la main aussitot."""
        if self.collecteurs:
            return self.collecteurs
        if self.config.get("demo_mode", False):
            etapes = (("demo", self._demo_step, 8),)
        else:
            periode = self.config.get("poll_seconds", 12)
            etapes = (("prieres", self._prieres_step, periode),
                      ("meteo", self._meteo_step, periode),
                      ("vols", self._live_step, periode))
        for nom, etape, periode in etapes:
            c = collecteur.Collecteur(nom, etape, periode, self.rapporte)
            c.demarre(self.arret)
            self.collecteurs.append(c)
        return self.collecteurs

    def arrete(self):
        self.arret.set()

    def run(self):
        """Compatibilite : demarre les collecteurs et attend l'arret."""
        self.demarre()
        self.arret.wait()
