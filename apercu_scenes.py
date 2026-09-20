"""Les scenes montrees par apercu.html, et leurs images.

Sorti d'apercu_html.py, qui n'a plus que le codage des pixels et la page.
Ajouter une scene ici suffit : elle apparait dans l'apercu sans autre
modification.

Les images sont produites par les vrais moteurs de rendu, jamais redessinees.
"""

import datetime
import json
import os

import adkar
import claudesource
import ecran_adkar
import ecran_alerte
import ecran_annonces
import ecran_claude
import ecran_liaison
import ecran_heure
import ecran_horaires
import ecran_meteo
import ecran_prieres
import icones_meteo
import meteosource
import panel
import prieresource
import transitions

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 10

VOL = {
    "callsign": "AFR1234", "airline_name": "Air France", "airline_icao": "AFR",
    "origin": "CDG", "destination": "JFK", "destination_city": "New York",
    "level": "FL340", "altitude_ft": 34000, "distance_km": 4.2,
}

SECOURS = {
    "nom": "MAGHREB", "adhan": "19:59", "iqama": "20:04", "phase": "adhan",
    "restant_min": 52, "restant": "52 MIN", "prise_main": False,
    "demain": False, "mosquee": "MOSQUEE", "heure": "19:07",
}


def _horaires_reels():
    """Priere courante de la mosquee configuree, ou None si indisponible."""
    try:
        with open(os.path.join(HERE, "config.json"), encoding="utf-8") as handle:
            config = json.load(handle)
        cache = prieresource.PrayerCache(
            os.path.join(HERE, prieresource.CACHE_FILE))
        return prieresource.poll(config, cache)
    except Exception:
        return None


# Releve de quota de secours : comme les vols et la priere du mode demo,
# il sert a juger la mise en page quand usage.json est absent ou perime.
USAGE_SECOURS = {
    "cle_a": "5H", "restant_a": 61, "reset_a": "4H25",
    "cle_b": "7J", "restant_b": 52, "reset_b": "5J7H",
}

# Annonces de secours : la mosquee n'en publie pas toujours, et l'apercu
# doit quand meme montrer a quoi ressemble le bandeau.
ANNONCES_SECOURS = ("CONFERENCE VENDREDI 20H", "COURS D'ARABE")

METEO_SECOURS = {
    "temperature": 18, "ressenti": 16, "vent_kmh": 12, "code": 3,
    "texte": "COUVERT", "icone": "nuage", "jour": True, "lieu": "PARIS",
}


def _meteo_reelle():
    """Meteo courante du lieu configure, ou None si indisponible."""
    try:
        with open(os.path.join(HERE, "config.json"), encoding="utf-8") as handle:
            config = json.load(handle)
        cache = meteosource.MeteoCache(
            os.path.join(HERE, meteosource.CACHE_FILE))
        return meteosource.poll(config, cache)
    except Exception:
        return None


def _heure_reelle():
    """Heure et date de maintenant, comme la passerelle les calculerait."""
    quand = datetime.datetime.now()
    return {"heure": quand.strftime("%H:%M"),
            "date": ecran_heure.format_date(quand)}


def _planche_icones():
    """Les sept icones cote a cote, pour les comparer d'un coup d'oeil."""
    frame = panel.Frame()
    x, y = 1, 2
    for nom in icones_meteo.ORDRE:
        if x + icones_meteo.LARGEUR > panel.WIDTH:
            x, y = 1, y + icones_meteo.HAUTEUR + 2
        frame.draw_sprite(x, y, icones_meteo.icone(nom), panel.TEXTE)
        x += icones_meteo.LARGEUR + 1
    return frame


def scenes():
    """Liste des ecrans a montrer : (titre, explication, images)."""
    base = _horaires_reels() or dict(SECOURS)

    # Une periode complete de defilement, pour que la boucle soit invisible
    vol = dict(VOL)
    vol["ticker"] = panel.build_ticker(vol)
    span = panel.font5x7.text_width(vol["ticker"]) + panel.SCROLL_GAP
    duree = span / panel.SCROLL_PX_PER_SEC
    images_vol = [panel.render(vol, i / float(FPS))
                  for i in range(int(duree * FPS))]

    imminente = dict(base, phase="iqama", prise_main=True,
                     restant="5 MIN", restant_min=5)
    en_cours = dict(base, phase="encours", prise_main=True,
                    restant="0 MIN", restant_min=0)
    joumoua = dict(base, nom="JOUMOUA", adhan="13:30", iqama="13:30",
                   phase="adhan", prise_main=False, restant="1H12",
                   heure="12:18")
    demain = dict(base, nom="FAJR", adhan="05:55", iqama="06:10", demain=True,
                  phase="adhan", prise_main=False, restant="6H25",
                  heure="23:30")

    # Transition vol -> priere, plus une pause a l'arrivee pour qu'on la voie
    def _vol(frame):
        panel.render(vol, 2.0, frame=frame)

    def _priere(frame):
        ecran_prieres.render(base, frame=frame)

    pas = max(1, int(transitions.TRANSITION_MS / 1000.0 * FPS))
    images_bascule = [transitions.compose(_vol, _priere, n / float(pas))
                      for n in range(pas + 1)]
    images_bascule += [images_bascule[-1]] * (FPS * 2)
    images_bascule = [transitions.compose(_vol, _priere, 0.0)] * FPS + images_bascule

    # Arrivee d'un avion : l'alerte le traverse, puis on bascule sur ses details
    pas_alerte = max(1, int(ecran_alerte.ALERTE_MS / 1000.0 * FPS))
    images_alerte = [ecran_alerte.render(vol, n / float(pas_alerte))
                     for n in range(pas_alerte + 1)]

    def _alerte(frame):
        ecran_alerte.render(vol, 1.0, frame=frame)

    images_alerte += [transitions.compose(_alerte, _vol, n / float(pas))
                      for n in range(pas + 1)]
    images_alerte += [panel.render(vol, 2.0 + n / float(FPS))
                      for n in range(FPS * 2)]

    # Priere qui prend la main : la mosquee glisse et se pose, puis les horaires
    images_annonce = [ecran_alerte.render_priere(imminente, n / float(pas_alerte))
                      for n in range(pas_alerte + 1)]

    def _annonce(frame):
        ecran_alerte.render_priere(imminente, 1.0, frame=frame)

    def _priere_imminente(frame):
        ecran_prieres.render(imminente, frame=frame)

    images_annonce += [transitions.compose(_annonce, _priere_imminente,
                                           n / float(pas))
                       for n in range(pas + 1)]
    images_annonce += [ecran_prieres.render(imminente)] * (FPS * 2)

    # Bandeau des horaires : un tour complet pour que la boucle soit
    # invisible, mais echantillonne. A la cadence des autres scenes il
    # faudrait 390 images pour une seule, et la page triplerait de poids.
    span = ecran_horaires.largeur_bandeau(base.get("jour") or [])
    tour = span / ecran_horaires.HORAIRES_PX_PAR_SEC if span else 1.0
    pas_bandeau = 120
    images_horaires = [ecran_horaires.render(base, tour * n / pas_bandeau)
                       for n in range(pas_bandeau)]

    # Meteo : l'icone entre et se pose, puis l'ecran complet
    meteo = _meteo_reelle() or dict(METEO_SECOURS)
    heure_courante = _heure_reelle().get("heure")
    images_meteo = [ecran_meteo.render_annonce(meteo, n / float(pas_alerte))
                    for n in range(pas_alerte + 1)]

    def _annonce_meteo(frame):
        ecran_meteo.render_annonce(meteo, 1.0, frame=frame)

    def _meteo(frame):
        ecran_meteo.render(meteo, frame=frame)

    images_meteo += [transitions.compose(_annonce_meteo, _meteo, n / float(pas))
                     for n in range(pas + 1)]
    images_meteo += [ecran_meteo.render(meteo)] * (FPS * 2)

    # Adkar : le nom du jour, un tour complet de sa ligne defilante.
    # Echantillonne comme le bandeau des horaires, pour ne pas alourdir la
    # page.
    rang_adkar = datetime.datetime.now().toordinal() % adkar.combien()
    tour_adkar = ecran_adkar.duree_defilement(adkar.entree(rang_adkar))
    pas_adkar = 80
    images_adkar = [ecran_adkar.render(rang_adkar,
                                       tour_adkar * n / pas_adkar,
                                       heure=heure_courante)
                    for n in range(pas_adkar)]

    # Annonces de la mosquee : un tour complet du bandeau, echantillonne
    # comme celui des horaires pour ne pas alourdir la page.
    titres = base.get("annonces") or ANNONCES_SECOURS
    info_an = dict(base, annonces=titres)
    tour_an = ecran_annonces.duree_tour(titres)
    pas_an = 100
    images_annonces = [ecran_annonces.render(info_an, tour_an * n / pas_an)
                       for n in range(pas_an)]

    # Claude Code : un tour complet de l'etoile, soit les huit phases.
    # Sans releve frais, on montre quand meme la mise en page avec des
    # chiffres de secours : l'apercu sert a juger l'ecran, pas le quota.
    usage = claudesource.poll({}) or dict(USAGE_SECOURS)
    images_claude = [
        ecran_claude.render(usage, n / ecran_claude.CLAUDE_PHASES_PAR_SEC,
                            heure=heure_courante)
        for n in range(ecran_claude.CLAUDE_PHASES)]

    return [
        ("Alerte avion", "Nouvel indicatif : la silhouette traverse le panneau "
         "de droite a gauche pendant %d ms, puis les details du vol arrivent."
         % ecran_alerte.ALERTE_MS, images_alerte),
        ("Annonce de priere", "La priere prend la main : la mosquee entre par "
         "la droite et se pose au centre en freinant, puis les horaires "
         "arrivent.", images_annonce),
        ("Vol au-dessus", "Un avion est dans le rayon : indicatif et niveau de "
         "vol, route, puis compagnie et destination en bandeau defilant.",
         images_vol),
        ("Transition", "Roulement vertical de %d ms entre deux ecrans : le "
         "sortant monte, l'entrant le suit par le bas."
         % transitions.TRANSITION_MS, images_bascule),
        ("Prochaine priere", "Ciel vide : l'ecran de veille annonce la priere "
         "a venir, l'iqama et le temps restant.",
         [ecran_prieres.render(base)]),
        ("Horaires du jour", "Bandeau defilant : les cinq prieres en arabe "
         "puis en francais, la prochaine en surbrillance. Un tour complet "
         "dure %.0f s." % (ecran_horaires.largeur_bandeau(base.get("jour") or [])
                           / ecran_horaires.HORAIRES_PX_PAR_SEC),
         images_horaires),
        ("Annonce meteo", "Au tour de la meteo : l'icone entre par la droite "
         "et se pose, puis le temps qu'il fait s'affiche.", images_meteo),
        ("Meteo", "Icone, temperature et ressenti, temps qu'il fait, lieu et "
         "vent. Les donnees viennent d'Open-Meteo.",
         [ecran_meteo.render(meteo)]),
        ("Icones meteo", "Les sept silhouettes : clair de jour et de nuit, "
         "eclaircies, couvert, pluie, neige, orage.",
         [_planche_icones()]),
        ("Heure", "L'heure seule, a l'echelle 3, avec la date en dessous. "
         "Elle vient de la passerelle : l'ESP32 n'a pas d'horloge.",
         [ecran_heure.render(_heure_reelle())]),
        ("Annonces", "Ce que la mosquee publie sur Mawaqit, en bandeau "
         "defilant. Seul le titre est exploitable : le corps de l'annonce "
         "est une image. Un tour dure %.0f s." % tour_an, images_annonces),
        ("Claude Code", "L'etoile a onze branches tourne, et les deux "
         "jauges montrent ce qu'il RESTE de quota : la fenetre de cinq "
         "heures et celle de la semaine, avec leur remise a zero.",
         images_claude),
        ("Nom du jour", "Un des 99 noms par jour : le nom en arabe, puis "
         "sa translitteration, son sens et sa signification en defilement. "
         "Un tour complet dure %.0f s." % tour_adkar, images_adkar),
        ("Prise de main", "Autour de l'horaire, la priere passe devant l'avion "
         "et le nom vire au blanc.",
         [ecran_prieres.render(imminente)]),
        ("Iqama en cours", "Entre l'iqama et la fin de la fenetre, le compte a "
         "rebours laisse la place a EN COURS.", [ecran_prieres.render(en_cours)]),
        ("Joumoua", "Le vendredi, l'heure annoncee par la mosquee remplace le "
         "dohr ; adhan et iqama confondus, la ligne du bas s'efface.",
         [ecran_prieres.render(joumoua)]),
        ("Fajr du lendemain", "Apres la derniere priere du jour, le panneau "
         "bascule sur le fajr suivant, marque +1.", [ecran_prieres.render(demain)]),
        ("Liaison perdue", "La passerelle ne repond plus depuis %d s. "
         "L'heure vient d'elle, donc elle n'est plus sure : le panneau le "
         "dit au lieu de laisser croire."
         % (ecran_liaison.LIAISON_SEUIL_MS // 1000),
         [ecran_liaison.render(4 * 60000)]),
        ("Pluie annoncee", "Une averse arrive dans l'heure : elle prend la "
         "place du lieu sur la ligne du bas, et passe en orange.",
         [ecran_meteo.render(dict(meteo, pluie_min=40,
                                  pluie_heure="17:30"))]),
        ("Ciel degage", "Ni avion ni horaires disponibles : l'ecran de veille "
         "d'origine.", [panel.render(None)]),
    ]


