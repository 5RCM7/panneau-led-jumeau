"""Tests hors ligne du pipeline, avec des reponses au format reel des APIs.

Lancer :  python3 test_hors_ligne.py
Aucun acces reseau requis.
"""

import datetime
import json
import os
import tempfile

from echantillons import (ADSB_SAMPLE, ADSBDB_SAMPLE, MAWAQIT_HTML,
                          MAWAQIT_SAMPLE)

import adkar
import arabe
import cadre
import annonces
import audio
import claudesource
import composition
import ecran_adkar
import ecran_alerte
import ecran_annonces
import ecran_claude
import ecran_liaison
import ecran_heure
import ecran_horaires
import ecran_meteo
import ecran_prieres
import flightsource
import font5x7
import horaires
import icones_meteo
import meteosource
import panel
import passerelle
import prieresource
import transitions
import verif_annonce
import verif_croquis
import verif_robustesse
import verif_jumeau

LAT, LON = 48.8566, 2.3522
checks = []


def check(label, condition, detail=""):
    checks.append((label, bool(condition), detail))


def main():
    # 1. Selection de l'avion : le plus proche, en vol, avec indicatif
    aircraft, distance = flightsource.pick_overhead(
        ADSB_SAMPLE["ac"], LAT, LON, min_alt_ft=1000, max_dist_km=20)
    check("un avion est retenu", aircraft is not None)
    check("l'avion le plus proche gagne",
          aircraft and aircraft["hex"] == "39e68a",
          aircraft["flight"].strip() if aircraft else "-")
    check("distance plausible", distance is not None and 0 < distance < 5,
          "%.2f km" % distance if distance else "-")

    # 2. L'avion au sol et celui sans indicatif sont ecartes
    sol_only = [a for a in ADSB_SAMPLE["ac"] if a["hex"] in ("3c6444", "abc123")]
    rien, _ = flightsource.pick_overhead(sol_only, LAT, LON, 1000, 20)
    check("avion au sol et sans indicatif ecartes", rien is None)

    # 3. Le filtre de distance fonctionne
    loin, _ = flightsource.pick_overhead(
        [ADSB_SAMPLE["ac"][1]], LAT, LON, 1000, 20)
    check("avion a 40 km ecarte", loin is None)

    # 4. Analyse de la reponse adsbdb, sans reseau
    info = ADSBDB_SAMPLE["response"]["flightroute"]
    route = {
        "airline_name": info["airline"]["name"],
        "airline_icao": info["airline"]["icao"],
        "airline_iata": info["airline"]["iata"],
        "origin": info["origin"]["iata_code"],
        "origin_city": info["origin"]["municipality"],
        "destination": info["destination"]["iata_code"],
        "destination_city": info["destination"]["municipality"],
    }

    flight = flightsource.build_flight(aircraft, distance, route)
    check("indicatif nettoye", flight["callsign"] == "AFR1234", flight["callsign"])
    check("niveau de vol calcule", flight["level"] == "FL340", flight["level"])
    check("destination lue", flight["destination"] == "JFK")
    check("ville de destination lue", flight["destination_city"] == "New York")

    # 5. Repli hexdb : chaine brute "LFPG-KJFK"
    repli = flightsource._lookup_route_hexdb.__doc__ is not None
    check("repli hexdb present", repli)

    # 6. Cache des routes : ecriture puis relecture
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cache.json")
        cache = flightsource.RouteCache(path)
        cache.put("AFR1234", route)
        relu = flightsource.RouteCache(path)
        check("cache relu depuis le disque",
              relu.get("AFR1234") == route)
        check("cache ignore les indicatifs inconnus",
              relu.get("XXX9999") is None)

    # 7. Rendu : le framebuffer a la bonne taille et n'est pas vide
    flight["ticker"] = panel.build_ticker(flight)
    frame = panel.render(flight, 0.0)
    data = frame.to_rgb_bytes()
    allumes = sum(1 for i in range(0, len(data), 3)
                  if data[i] or data[i + 1] or data[i + 2])
    check("taille du framebuffer", len(data) == 128 * 32 * 3, str(len(data)))
    check("des pixels sont allumes", allumes > 200, "%d LED" % allumes)

    # 8. Rien ne deborde a droite ni en bas
    marge_droite = all(
        data[(y * 128 + 127) * 3:(y * 128 + 127) * 3 + 3] == b"\x00\x00\x00"
        for y in range(32))
    check("colonne de marge a droite respectee", marge_droite)

    # 9. Le defilement change bien l'image
    frame_t6 = panel.render(flight, 6.0)
    check("le bandeau defile", frame_t6.to_rgb_bytes() != data)

    # 10. Ciel vide : pas de plantage
    vide = panel.render(None, 0.0)
    check("ecran de veille rendu", len(vide.to_rgb_bytes()) == 128 * 32 * 3)

    # 11. Charge utile ESP32 assez petite
    import server
    payload = json.dumps(server.compact_flight(flight))
    check("charge utile ESP32 compacte", len(payload) < 400, "%d octets" % len(payload))

    # 12. Un ticker tres long ne deborde pas du tampon du firmware (144 octets).
    # Pire cas : chaque champ texte rempli jusqu'a son tampon C.
    long_flight = dict(flight, airline_name="A" * 27,
                       destination_city="V" * 27, aircraft="M" * 31,
                       distance_km=9999)
    ticker = panel.build_ticker(long_flight)
    check("ticker au pire cas sous la limite firmware", len(ticker) < 144,
          "%d caracteres sur 144" % len(ticker))

    # 12b. Marque et modele de l'appareil, juste avant la distance
    check("marque et modele assembles",
          flightsource.nom_appareil(
              {"manufacturer": "Boeing", "type": "777 328ER"}, "B77W")
          == "BOEING 777 328ER")
    check("repli sur le code type quand adsbdb ne connait pas",
          flightsource.nom_appareil({}, "A346") == "A346")
    check("rien du tout : chaine vide",
          flightsource.nom_appareil(None, None) == "")
    check("modele seul, sans marque",
          flightsource.nom_appareil({"type": "Falcon 7X"}, "F7X")
          == "FALCON 7X")

    avec_avion = dict(flight, aircraft="BOEING 777 328ER", distance_km=4.2)
    morceaux = panel.build_ticker(avec_avion).split(font5x7.ARROW)
    check("l'appareil figure dans le bandeau",
          any("BOEING 777 328ER" in m for m in morceaux))
    check("l'appareil precede la distance",
          [i for i, m in enumerate(morceaux) if "BOEING" in m][0]
          < [i for i, m in enumerate(morceaux) if "KM" in m][0],
          " | ".join(m.strip() for m in morceaux))
    sans_avion = dict(flight, aircraft="", distance_km=4.2)
    check("bandeau sans appareil : pas de separateur en trop",
          panel.build_ticker(sans_avion).count(font5x7.ARROW) == 2,
          panel.build_ticker(sans_avion))

    # 12d. Le panneau est une horloge murale : l'heure sur chaque ecran de la
    # rotation, jamais sur une annonce ni pendant une transition
    HORLOGE = "23:07"
    vol_horloge = panel.render(flight, 0.0, heure=HORLOGE)
    vol_sans = panel.render(flight, 0.0, heure="00:00")
    check("l'ecran vol porte l'heure",
          vol_horloge.to_rgb_bytes() != vol_sans.to_rgb_bytes())
    check("l'heure du vol tient a droite de la route",
          panel.TEXT_X0 + font5x7.text_width("CDG %s JFK" % font5x7.ARROW)
          < panel.TEXT_X1 - font5x7.text_width(HORLOGE) + 1,
          "route finit a %d, heure commence a %d"
          % (panel.TEXT_X0 + font5x7.text_width("CDG %s JFK" % font5x7.ARROW),
             panel.TEXT_X1 - font5x7.text_width(HORLOGE) + 1))
    check("marge droite respectee avec l'heure",
          all(vol_horloge.buf[(y * 128 + 127) * 3:(y * 128 + 127) * 3 + 3]
              == b"\x00\x00\x00" for y in range(32)))

    veille_a = panel.render(None, heure="23:07")
    veille_b = panel.render(None, heure="11:11")
    check("l'ecran de veille porte l'heure",
          veille_a.to_rgb_bytes() != veille_b.to_rgb_bytes())

    # 12c. Les APIs renvoient des noms accentues que la police ignore
    check("accents retires des villes",
          font5x7.affichable("S\u00e3o Paulo") == "Sao Paulo",
          font5x7.affichable("S\u00e3o Paulo"))
    check("accents francais retires",
          font5x7.affichable("N\u00eemes") == "Nimes")
    check("caracteres hors police jetes plutot que rendus en ?",
          font5x7.affichable("Torsh\u00e6vn \u4e2d") == "Torshvn ",
          repr(font5x7.affichable("Torsh\u00e6vn \u4e2d")))
    check("texte deja propre inchange",
          font5x7.affichable("NEW YORK") == "NEW YORK")
    check("valeur vide toleree",
          font5x7.affichable("") == "" and font5x7.affichable(None) is None)

    accentue = flightsource.build_flight(
        aircraft, distance,
        dict(route, destination_city="S\u00e3o Paulo",
             airline_name="Air Cara\u00efbes"),
        {"manufacturer": "Embraer", "type": "190"})
    check("la ville accentuee arrive propre dans le vol",
          accentue["destination_city"] == "Sao Paulo",
          accentue["destination_city"])
    check("la compagnie accentuee arrive propre",
          accentue["airline_name"] == "Air Caraibes",
          accentue["airline_name"])
    check("tout le bandeau est dessinable par la police",
          all(c.upper() in font5x7.GLYPHS
              for c in panel.build_ticker(accentue)),
          panel.build_ticker(accentue))

    # 13. Extraction de confData depuis le HTML de la page mosquee
    conf = prieresource._extract_conf(MAWAQIT_HTML)
    check("confData extrait du HTML", conf.get("jumua") == "13:30")
    check("accolades dans les chaines ignorees",
          conf.get("name") == "Mosquee {test} \"Exemple\"")

    # 14. Lecture du calendrier : adhan, iqama en decalage, iqama en heure fixe
    prieres, chourouk = horaires.day_times(
        MAWAQIT_SAMPLE, datetime.date(2026, 9, 19))
    noms = [p["nom"] for p in prieres]
    check("cinq prieres lues", noms == list(horaires.NOMS), " ".join(noms))
    check("chourouk separe des prieres",
          horaires._hhmm(chourouk) == "07:33",
          horaires._hhmm(chourouk))
    check("adhan du maghreb lu",
          horaires._hhmm(prieres[3]["adhan"]) == "19:59",
          horaires._hhmm(prieres[3]["adhan"]))
    check("iqama en decalage appliquee",
          horaires._hhmm(prieres[3]["iqama"]) == "20:04",
          horaires._hhmm(prieres[3]["iqama"]))

    hiver, _ = horaires.day_times(MAWAQIT_SAMPLE, datetime.date(2026, 1, 19))
    check("iqama en heure fixe respectee",
          horaires._hhmm(hiver[4]["iqama"]) == "19:20",
          horaires._hhmm(hiver[4]["iqama"]))

    # 15. Vendredi : la priere de midi devient la Joumoua, a l'heure annoncee
    vendredi, _ = horaires.day_times(MAWAQIT_SAMPLE, datetime.date(2026, 9, 25))
    check("joumoua le vendredi", vendredi[1]["nom"] == "JOUMOUA", vendredi[1]["nom"])
    check("joumoua : adhan et iqama a l'heure annoncee",
          horaires._hhmm(vendredi[1]["adhan"]) == "13:30"
          and vendredi[1]["iqama"] == vendredi[1]["adhan"],
          horaires._hhmm(vendredi[1]["adhan"]))

    # 16. Choix de la priere a afficher selon l'heure
    def a(heure, minute):
        return horaires.next_prayer(
            MAWAQIT_SAMPLE, datetime.datetime(2026, 9, 19, heure, minute))

    check("priere a venir annoncee", a(5, 0)["nom"] == "FAJR", a(5, 0)["restant"])
    check("on reste sur la priere jusqu'a l'iqama",
          a(6, 0)["nom"] == "FAJR" and a(6, 0)["phase"] == "iqama",
          a(6, 0)["restant"])
    check("priere passee : on avance a la suivante",
          a(20, 11)["nom"] == "ICHA", a(20, 11)["nom"])
    check("prise de main juste avant l'adhan", a(5, 52)["prise_main"] is True)
    check("pas de prise de main une heure avant",
          a(5, 0)["prise_main"] is False)
    check("apres la derniere priere : fajr du lendemain",
          a(23, 30)["demain"] is True and a(23, 30)["nom"] == "FAJR",
          a(23, 30)["restant"])

    # 17. Format du temps restant, qui doit tenir sur le panneau
    check("temps restant en minutes",
          horaires.format_restant(12) == "12 MIN")
    check("temps restant en heures",
          horaires.format_restant(440) == "7H20",
          horaires.format_restant(440))

    # 18. Nom de mosquee reduit a de l'ASCII affichable
    check("nom de mosquee ASCII depuis le slug",
          horaires.nom_court(MAWAQIT_SAMPLE, "mosquee-de-ta-ville") == "MOSQUEE")
    sans_slug = horaires.nom_court(MAWAQIT_SAMPLE, "")
    check("nom de mosquee desaccentue a defaut",
          sans_slug.isascii() and sans_slug.startswith("MOSQUEE"), sans_slug)

    # 19. Cache des horaires : ecriture puis relecture
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "prieres.json")
        cache = prieresource.PrayerCache(path)
        cache.put("mosquee-de-ta-ville", MAWAQIT_SAMPLE)
        relu = prieresource.PrayerCache(path)
        check("cache des horaires relu depuis le disque",
              relu.get("mosquee-de-ta-ville") is not None)
        check("cache des horaires ignore les mosquees inconnues",
              relu.get("inconnue") is None)

    # 20. Rendu de l'ecran priere
    info = a(19, 50)
    info["mosquee"] = "MOSQUEE"
    ecran_p = ecran_prieres.render(info, now="19:50")
    pixels = ecran_p.to_rgb_bytes()
    allumes_p = sum(1 for i in range(0, len(pixels), 3)
                    if pixels[i] or pixels[i + 1] or pixels[i + 2])
    check("ecran priere rendu", len(pixels) == 128 * 32 * 3)
    check("des pixels sont allumes sur l'ecran priere", allumes_p > 200,
          "%d LED" % allumes_p)
    marge_p = all(
        pixels[(y * 128 + 127) * 3:(y * 128 + 127) * 3 + 3] == b"\x00\x00\x00"
        for y in range(32))
    check("marge droite respectee sur l'ecran priere", marge_p)

    # 21. Charge utile ESP32 avec les deux ecrans dans le meme envoi
    complet = json.dumps(server.compact_flight(flight, info, "vol"))
    check("charge utile vol + priere compacte", len(complet) < 400,
          "%d octets" % len(complet))

    # Pire cas : tous les champs texte remplis jusqu'aux tampons du firmware
    pire = dict(flight)
    pire["airline_name"] = "A" * 27      # char airline[28]
    pire["destination_city"] = "V" * 27  # char city[28]
    pire["callsign"] = "C" * 11          # char callsign[12]
    pire_info = dict(info, nom="JOUMOUA", mosquee="M" * 9,
                     restant="23H59", jour=[{"nom": "X", "adhan": "23:59"}] * 5)
    pire_meteo = {"temperature": -12, "ressenti": -18, "vent_kmh": 120,
                  "icone": "eclaircie", "texte": "BROUILLARD", "lieu": "V" * 11}
    pire_heure = {"heure": "23:59", "date": "D" * 19, "luminosite": 255}
    # Tous les blocs, chacun rempli jusqu'a son tampon C : l'ancien pire cas
    # omettait annonces, quota, audio et adkar, et passait sous le budget
    # alors que la vraie charge pleine le depassait.
    pire["aircraft"] = "B" * 31           # char avion[32]
    pire_info["mosquee"] = "M" * 11       # char mosquee[12]
    pire_info["annonces"] = ["X" * 48, "Y" * 48, "Z" * 52]  # annonces[152]
    pire_meteo.update(texte="T" * 15, pluie_min=120, pluie_heure="23:59",
                      heure="23:59")
    pire_usage = {"cle_a": "5H", "restant_a": 100, "reset_a": "23H59",
                  "cle_b": "7J", "restant_b": 100, "reset_b": "23H59"}
    pire_son = {"son": 2, "cue": "C" * 23, "volume": 30}  # char cue[24]
    charge_max = json.dumps(server.compact_flight(
        pire, pire_info, "horaires", pire_meteo, pire_heure, 98, pire_usage,
        pire_son))
    check("charge utile au pire cas sous la limite",
          len(charge_max) < composition.BUDGET_OCTETS,
          "%d octets sur %d" % (len(charge_max), composition.BUDGET_OCTETS))

    # Le firmware ne connait que les ecrans de fond : une annonce doit lui
    # arriver sous le nom de l'ecran qu'elle habille, sinon il tombe en veille
    for annonce, fond in composition.ECRAN_DE_FOND.items():
        envoye = server.compact_flight(flight, info, annonce, pire_meteo)
        check("annonce %s transmise comme %s" % (annonce, fond),
              envoye.get("sc") == fond, envoye.get("sc"))

    # 22. Conversion des logos en RGB565 (arithmetique pure, sans Pillow)
    import export_logos
    check("rgb565 : rouge pur", export_logos.rgb565((255, 0, 0)) == 0xF800,
          "0x%04X" % export_logos.rgb565((255, 0, 0)))
    check("rgb565 : vert pur", export_logos.rgb565((0, 255, 0)) == 0x07E0,
          "0x%04X" % export_logos.rgb565((0, 255, 0)))
    check("rgb565 : bleu pur", export_logos.rgb565((0, 0, 255)) == 0x001F,
          "0x%04X" % export_logos.rgb565((0, 0, 255)))
    check("rgb565 : blanc", export_logos.rgb565((255, 255, 255)) == 0xFFFF)
    check("rgb565 : noir reste transparent",
          export_logos.rgb565((0, 0, 0)) == 0x0000)

    # 22b. Transitions : courbe, bornes, et superposition des deux ecrans
    check("courbe de transition bornee a 0",
          transitions.adoucis(0.0) == 0.0)
    check("courbe de transition bornee a 1",
          transitions.adoucis(1.0) == 1.0)
    check("courbe de transition symetrique au milieu",
          abs(transitions.adoucis(0.5) - 0.5) < 1e-9)
    check("courbe de transition ecrete hors bornes",
          transitions.adoucis(-2.0) == 0.0 and transitions.adoucis(9.0) == 1.0)

    def _vol(frame):
        panel.render(flight, 0.0, frame=frame)

    def _priere(frame):
        ecran_prieres.render(info, now="19:50", frame=frame)

    debut = transitions.compose(_vol, _priere, 0.0).to_rgb_bytes()
    fin = transitions.compose(_vol, _priere, 1.0).to_rgb_bytes()
    milieu = transitions.compose(_vol, _priere, 0.5).to_rgb_bytes()
    check("transition a 0 : l'ecran sortant, intact",
          debut == panel.render(flight, 0.0).to_rgb_bytes())
    check("transition a 1 : l'ecran entrant, intact",
          fin == ecran_prieres.render(info, now="19:50").to_rgb_bytes())
    check("transition a mi-course : ni l'un ni l'autre",
          milieu != debut and milieu != fin)

    # Un decalage vertical deplace bien les pixels, sans deborder du tampon
    tampon = panel.Frame()
    tampon.dy = 5
    tampon.set(10, 0, (255, 255, 255))
    tampon.set(10, 40, (255, 255, 255))  # hors cadre apres decalage
    i = (5 * 128 + 10) * 3
    check("decalage vertical applique", tampon.buf[i] == 255)
    check("decalage vertical n'ecrit pas hors du cadre",
          len(tampon.buf) == 128 * 32 * 3
          and sum(1 for n in range(0, len(tampon.buf), 3) if tampon.buf[n]) == 1)

    # 22c. Ecran d'alerte : l'avion traverse de droite a gauche
    check("avion a droite au debut de l'alerte",
          ecran_alerte.position_avion(0.0) == panel.WIDTH,
          str(ecran_alerte.position_avion(0.0)))
    check("avion sorti par la gauche a la fin",
          ecran_alerte.position_avion(1.0) == -ecran_alerte.AVION_W,
          str(ecran_alerte.position_avion(1.0)))
    check("avion ecrete hors bornes",
          ecran_alerte.position_avion(-5) == panel.WIDTH
          and ecran_alerte.position_avion(5) == -ecran_alerte.AVION_W)
    check("l'avion avance de droite a gauche",
          ecran_alerte.position_avion(0.3) > ecran_alerte.position_avion(0.7))

    alerte = ecran_alerte.render(flight, 0.5)
    pix_alerte = alerte.to_rgb_bytes()
    check("ecran d'alerte rendu", len(pix_alerte) == 128 * 32 * 3)
    check("l'annonce et l'indicatif sont allumes",
          sum(1 for n in range(0, len(pix_alerte), 3)
              if pix_alerte[n] or pix_alerte[n + 1] or pix_alerte[n + 2]) > 150)
    check("l'avion bouge d'une image a l'autre",
          ecran_alerte.render(flight, 0.2).to_rgb_bytes() != pix_alerte)
    check("l'annonce tient dans la largeur",
          panel.font5x7.text_width(ecran_alerte.ANNONCE) <= panel.WIDTH,
          "%d px" % panel.font5x7.text_width(ecran_alerte.ANNONCE))
    check("l'annonce de priere tient dans la largeur",
          panel.font5x7.text_width(ecran_alerte.ANNONCE_PRIERE) <= panel.WIDTH,
          "%d px" % panel.font5x7.text_width(ecran_alerte.ANNONCE_PRIERE))

    # La mosquee entre par la droite et se pose au centre, en freinant
    centre = (panel.WIDTH - ecran_alerte.MOSQUEE_W) // 2
    check("mosquee a droite au debut",
          ecran_alerte.position_mosquee(0.0) == panel.WIDTH,
          str(ecran_alerte.position_mosquee(0.0)))
    check("mosquee posee au centre a la fin",
          ecran_alerte.position_mosquee(1.0) == centre, str(centre))
    check("mosquee ecretee hors bornes",
          ecran_alerte.position_mosquee(-1) == panel.WIDTH
          and ecran_alerte.position_mosquee(3) == centre)
    # Adoucie : au quart du temps elle a parcouru nettement moins du quart
    parcouru = (panel.WIDTH - ecran_alerte.position_mosquee(0.25)) \
        / float(panel.WIDTH - centre)
    check("la mosquee freine au lieu d'avancer lineairement", parcouru < 0.2,
          "%.0f %% du trajet au quart du temps" % (parcouru * 100))

    alerte_p = ecran_alerte.render_priere(info, 1.0)
    pix_p = alerte_p.to_rgb_bytes()
    check("ecran d'annonce de priere rendu", len(pix_p) == 128 * 32 * 3)
    check("la mosquee et l'annonce sont allumees",
          sum(1 for n in range(0, len(pix_p), 3)
              if pix_p[n] or pix_p[n + 1] or pix_p[n + 2]) > 200)
    check("la mosquee bouge d'une image a l'autre",
          ecran_alerte.render_priere(info, 0.3).to_rgb_bytes() != pix_p)
    check("marge droite respectee sur l'annonce de priere",
          all(pix_p[(y * 128 + 127) * 3:(y * 128 + 127) * 3 + 3] == b"\x00\x00\x00"
              for y in range(32)))

    # 22e. Tableau des cinq horaires
    jour_complet = horaires.next_prayer(
        MAWAQIT_SAMPLE, datetime.datetime(2026, 9, 19, 10, 0))
    check("la journee entiere est exposee",
          len(jour_complet.get("jour") or []) == 5,
          "%d prieres" % len(jour_complet.get("jour") or []))
    check("le rang de la priere a venir est connu",
          jour_complet.get("rang") == 1, str(jour_complet.get("rang")))
    check("les horaires du tableau sont ceux du calendrier",
          [p["adhan"] for p in jour_complet["jour"]]
          == ["05:54", "13:45", "17:09", "19:59", "21:22"])

    jour_complet["mosquee"] = "MOSQUEE"
    tableau = ecran_horaires.render(jour_complet)
    pix_t = tableau.to_rgb_bytes()
    check("tableau des horaires rendu", len(pix_t) == 128 * 32 * 3)
    check("les cinq horaires sont allumes",
          sum(1 for n in range(0, len(pix_t), 3)
              if pix_t[n] or pix_t[n + 1] or pix_t[n + 2]) > 300)
    check("marge droite respectee sur le tableau",
          all(pix_t[(y * 128 + 127) * 3:(y * 128 + 127) * 3 + 3] == b"\x00\x00\x00"
              for y in range(32)))

    # Le bandeau defile, se repete, et tient dans la hauteur
    check("le bandeau des horaires defile",
          ecran_horaires.render(jour_complet, 0.0).to_rgb_bytes()
          != ecran_horaires.render(jour_complet, 3.0).to_rgb_bytes())
    span = ecran_horaires.largeur_bandeau(jour_complet["jour"])
    check("le bandeau se repete a l'identique",
          ecran_horaires.render(jour_complet, 0.0).to_rgb_bytes()
          == ecran_horaires.render(
              jour_complet,
              span / ecran_horaires.HORAIRES_PX_PAR_SEC).to_rgb_bytes(),
          "%d px, %.1f s" % (span, span / ecran_horaires.HORAIRES_PX_PAR_SEC))
    check("le bandeau tient dans la hauteur du panneau",
          ecran_horaires.HORAIRES_BANDE_Y + arabe.HAUTEUR <= panel.HEIGHT,
          "bas a %d sur %d"
          % (ecran_horaires.HORAIRES_BANDE_Y + arabe.HAUTEUR, panel.HEIGHT))
    check("un tour de bandeau tient dans la duree de l'ecran",
          span / ecran_horaires.HORAIRES_PX_PAR_SEC <= 45,
          "%.1f s pour 45 s d'affichage"
          % (span / ecran_horaires.HORAIRES_PX_PAR_SEC))

    # Les six noms arabes existent et sont de la bonne hauteur
    check("chaque priere a son nom en arabe",
          all(arabe.mot(n) for n in
              ("FAJR", "DOHR", "ASR", "MAGHREB", "ICHA", "JOUMOUA")))
    check("les silhouettes arabes ont toutes la meme hauteur",
          all(len(arabe.mot(n)) == arabe.HAUTEUR for n in arabe.MOTS),
          "%d px" % arabe.HAUTEUR)
    check("silhouettes arabes rectangulaires",
          all(len(set(len(l) for l in arabe.mot(n))) == 1 for n in arabe.MOTS))

    # Le vendredi, la case de midi porte JOU
    vendredi_info = horaires.next_prayer(
        MAWAQIT_SAMPLE, datetime.datetime(2026, 9, 25, 10, 0))
    check("abrege joumoua le vendredi",
          ecran_horaires.abrege(vendredi_info["jour"][1]["nom"], 1) == "JOU",
          ecran_horaires.abrege(vendredi_info["jour"][1]["nom"], 1))
    check("abrege normal les autres jours",
          ecran_horaires.abrege(jour_complet["jour"][1]["nom"], 1) == "DOH")

    # 22f. Meteo : lecture du code WMO, mise en forme, rendu
    check("code WMO clair de jour -> soleil",
          meteosource.decrit(0, True) == ("CLAIR", "soleil"))
    check("code WMO clair de nuit -> lune",
          meteosource.decrit(0, False) == ("CLAIR", "lune"))
    check("code WMO couvert", meteosource.decrit(3, True)[1] == "nuage")
    check("codes WMO d'averse ranges avec la pluie",
          meteosource.decrit(81, True)[1] == "pluie")
    check("code WMO d'orage", meteosource.decrit(95, True)[1] == "orage")
    check("code WMO inconnu : repli sans planter",
          meteosource.decrit(1234, True)[1] == "nuage")
    check("toutes les icones annoncees existent",
          all(nom in icones_meteo.PAR_NOM
              for _, _, nom in meteosource._TEMPS) and "lune" in icones_meteo.PAR_NOM)
    check("les icones font toutes la bonne taille",
          all(len(icones_meteo.icone(n)) == icones_meteo.HAUTEUR
              and all(len(r) == icones_meteo.LARGEUR
                      for r in icones_meteo.icone(n))
              for n in icones_meteo.ORDRE),
          "%dx%d" % (icones_meteo.LARGEUR, icones_meteo.HAUTEUR))

    check("temperature negative formatee",
          ecran_meteo.temperature(-3) == "-3%sC" % panel.font5x7.DEGRE)
    check("temperature absente : chaine vide",
          ecran_meteo.temperature(None) == "")

    METEO = {"temperature": 18, "ressenti": 16, "vent_kmh": 12, "code": 3,
             "texte": "COUVERT", "icone": "nuage", "jour": True,
             "lieu": "PARIS"}
    ecran_m = ecran_meteo.render(METEO)
    pix_m = ecran_m.to_rgb_bytes()
    check("ecran meteo rendu", len(pix_m) == 128 * 32 * 3)
    check("l'ecran meteo est bien rempli",
          sum(1 for n in range(0, len(pix_m), 3)
              if pix_m[n] or pix_m[n + 1] or pix_m[n + 2]) > 250)
    check("marge droite respectee sur l'ecran meteo",
          all(pix_m[(y * 128 + 127) * 3:(y * 128 + 127) * 3 + 3] == b"\x00\x00\x00"
              for y in range(32)))
    check("meteo absente : repli sur la veille sans planter",
          len(ecran_meteo.render(None).to_rgb_bytes()) == 128 * 32 * 3)

    check("icone meteo a droite au debut de l'annonce",
          ecran_meteo.position_icone(0.0) == panel.WIDTH)
    check("icone meteo posee au centre a la fin",
          ecran_meteo.position_icone(1.0)
          == (panel.WIDTH - icones_meteo.LARGEUR) // 2)
    annonce_m = ecran_meteo.render_annonce(METEO, 1.0)
    check("annonce meteo rendue",
          len(annonce_m.to_rgb_bytes()) == 128 * 32 * 3)
    check("l'annonce meteo bouge d'une image a l'autre",
          ecran_meteo.render_annonce(METEO, 0.3).to_rgb_bytes()
          != annonce_m.to_rgb_bytes())

    # Cache meteo : ecriture, relecture, et repli sur une valeur perimee
    with tempfile.TemporaryDirectory() as tmp:
        chemin = os.path.join(tmp, "meteo.json")
        cache_m = meteosource.MeteoCache(chemin)
        cache_m.put("49,2", {"temperature_2m": 18})
        relu_m = meteosource.MeteoCache(chemin)
        check("cache meteo relu depuis le disque",
              relu_m.get("49,2") is not None)
        relu_m.data["49,2"]["ts"] = 0  # on le fait vieillir
        check("cache meteo perime ignore", relu_m.get("49,2") is None)
        check("cache meteo perime servi en dernier recours",
              relu_m.get("49,2", ignore_ttl=True) is not None)

    # 22h. Ecran de l'heure
    quand = datetime.datetime(2026, 9, 25, 7, 5)
    check("date formatee en francais sans accent",
          ecran_heure.format_date(quand) == "VENDREDI 25 SEPT",
          ecran_heure.format_date(quand))
    check("la date la plus longue tient sur le panneau",
          max(panel.font5x7.text_width(
              ecran_heure.format_date(datetime.datetime(2026, m, 28)))
              for m in range(1, 13)) <= panel.WIDTH,
          "%d px" % max(panel.font5x7.text_width(
              ecran_heure.format_date(datetime.datetime(2026, m, 28)))
              for m in range(1, 13)))

    HEURE = {"heure": "22:33", "date": "VENDREDI 25 SEPT"}
    ecran_h = ecran_heure.render(HEURE)
    pix_h = ecran_h.to_rgb_bytes()
    check("ecran de l'heure rendu", len(pix_h) == 128 * 32 * 3)
    check("l'heure agrandie occupe l'ecran",
          sum(1 for n in range(0, len(pix_h), 3)
              if pix_h[n] or pix_h[n + 1] or pix_h[n + 2]) > 350)
    check("l'heure agrandie tient dans la largeur",
          cadre.largeur_echelle("22:33", ecran_heure.HEURE_ECHELLE)
          <= panel.WIDTH,
          "%d px" % cadre.largeur_echelle("22:33", ecran_heure.HEURE_ECHELLE))
    check("l'heure agrandie tient dans la hauteur",
          ecran_heure.HEURE_Y + 7 * ecran_heure.HEURE_ECHELLE
          <= ecran_heure.DATE_Y,
          "bas a %d, date a %d"
          % (ecran_heure.HEURE_Y + 7 * ecran_heure.HEURE_ECHELLE,
             ecran_heure.DATE_Y))
    check("marge droite respectee sur l'ecran de l'heure",
          all(pix_h[(y * 128 + 127) * 3:(y * 128 + 127) * 3 + 3] == b"\x00\x00\x00"
              for y in range(32)))
    check("heure absente : repli sans planter",
          len(ecran_heure.render(None).to_rgb_bytes()) == 128 * 32 * 3)

    # Le texte agrandi doit vraiment etre plus gros
    petit = panel.Frame()
    petit.draw_text(0, 0, "8", panel.PRINCIPAL)
    gros = panel.Frame()
    gros.draw_text_echelle(0, 0, "8", panel.PRINCIPAL, 3)
    n_petit = sum(1 for n in range(0, len(petit.buf), 3) if petit.buf[n])
    n_gros = sum(1 for n in range(0, len(gros.buf), 3) if gros.buf[n])
    check("un glyphe a l'echelle 3 couvre neuf fois plus de pixels",
          n_gros == n_petit * 9, "%d contre %d" % (n_gros, n_petit))

    # 22k. Tempo par ecran, et priorite des ecrans de priere
    tempos = {"vol": 25, "priere": 40, "horaires": 45, "annonces": 30,
              "meteo": 25, "adkar": 30, "claude": 15, "heure": 20}
    cadence = passerelle.Gateway({"duree_ecrans": tempos,
                                  "rotation_seconds": 30})
    for nom, attendu in tempos.items():
        if nom in ("adkar", "annonces"):
            continue  # tempos adaptatifs, verifies plus bas
        check("tempo de l'ecran %s" % nom,
              cadence.duree_ecran(nom) == attendu, "%d s" % attendu)
    check("tempo par defaut pour un ecran non liste",
          cadence.duree_ecran("veille") == 30)
    check("le bandeau des horaires a le tour le plus long",
          tempos["horaires"] == max(tempos.values()))
    total = sum(tempos.values())
    check("un cycle complet dure entre deux et quatre minutes",
          120 <= total <= 240, "%d s" % total)

    # Un avion qui arrive ne doit pas couper un ecran de priere
    prio = passerelle.Gateway({"duree_ecrans": tempos})
    prio.prieres = dict(info, prise_main=False)
    prio.meteo = None
    prio.flight = dict(flight)
    prio.last_seen = __import__("time").time()
    for ecran_en_cours in passerelle.ECRANS_PRIERE:
        prio.rotation_ecran = ecran_en_cours
        prio.rotation_debut = __import__("time").time()
        prio.callsign_annonce = None  # un avion jamais annonce
        obtenu = prio.screen()[0]
        check("un avion n'interrompt pas l'ecran %s" % ecran_en_cours,
              obtenu == ecran_en_cours, obtenu)
    prio.rotation_ecran = "meteo"
    prio.rotation_debut = __import__("time").time()
    prio.callsign_annonce = None
    check("hors ecran de priere, l'avion s'annonce",
          prio.screen()[0] == "alerte", prio.screen()[0])

    # 22l. Le verrou de la passerelle est reentrant. _rotation le tient en
    # appelant duree_ecran ; sur l'ecran des annonces sans prieres sous la
    # main, celle-ci relit current_prieres, qui le reprend. Avec un verrou
    # simple, la passerelle se bloquait pour de bon.
    import threading
    fige = passerelle.Gateway({"duree_ecrans": tempos})
    fige.rotation_ecran = "annonces"
    fige.rotation_debut = __import__("time").time()
    fil = threading.Thread(target=fige._rotation, args=(None, None, None),
                           daemon=True)
    fil.start()
    fil.join(2.0)
    check("verrou : la rotation ne se bloque pas sur elle-meme",
          not fil.is_alive())

    # 22m. Hysteresis : l'avion affiche garde l'ecran tant qu'il est dans le
    # rayon, sauf si un autre est nettement plus proche. Sans elle, deux
    # avions a distance voisine se relaient a chaque sondage, et chaque
    # relais relance l'annonce.
    def avion_a(indicatif, km):
        # un degre de latitude vaut ~111,2 km
        return {"hex": indicatif.lower(), "flight": indicatif + " ",
                "lat": LAT + km / 111.195, "lon": LON, "alt_baro": 30000}

    duo = [avion_a("AAA111", 3.0), avion_a("BBB222", 3.4)]
    choisi, _ = flightsource.pick_overhead(duo, LAT, LON, 1000, 20)
    check("hysteresis : sans avion courant, le plus proche gagne",
          choisi["flight"].strip() == "AAA111")
    garde, d_garde = flightsource.pick_overhead(
        duo, LAT, LON, 1000, 20, courant="BBB222", marge_km=1.0)
    check("hysteresis : l'avion courant garde l'ecran a 400 m pres",
          garde["flight"].strip() == "BBB222",
          "%s a %.2f km" % (garde["flight"].strip(), d_garde))
    loin_duo = [avion_a("AAA111", 1.0), avion_a("BBB222", 3.4)]
    bascule, _ = flightsource.pick_overhead(
        loin_duo, LAT, LON, 1000, 20, courant="BBB222", marge_km=1.0)
    check("hysteresis : un avion plus proche de plus d'un km prend la main",
          bascule["flight"].strip() == "AAA111")
    sorti = [avion_a("AAA111", 3.0), avion_a("BBB222", 25.0)]
    parti, _ = flightsource.pick_overhead(
        sorti, LAT, LON, 1000, 20, courant="BBB222", marge_km=1.0)
    check("hysteresis : l'avion courant sorti du rayon cede la place",
          parti["flight"].strip() == "AAA111")
    check("hysteresis : l'indicatif courant se compare sans casse ni espace",
          flightsource.pick_overhead(duo, LAT, LON, 1000, 20,
                                     courant=" bbb222",
                                     marge_km=1.0)[0]["flight"].strip()
          == "BBB222")

    # Deux avions qui se croisent : sur dix sondages, un seul changement
    # d'indicatif, donc une seule annonce, au lieu d'un a chaque sondage.
    import unittest.mock
    passes = [[avion_a("AAA111", 3.0 + 0.1 * (n % 2)),
               avion_a("BBB222", 3.05 - 0.1 * (n % 2))] for n in range(10)]
    croise = passerelle.Gateway({"latitude": LAT, "longitude": LON,
                                 "bascule_km": 1.0})
    vus = []
    with unittest.mock.patch.object(flightsource, "fetch_nearby",
                                    side_effect=passes), \
            unittest.mock.patch.object(flightsource, "lookup_route",
                                       return_value={}), \
            unittest.mock.patch.object(flightsource, "lookup_aircraft",
                                       return_value={}):
        for _ in passes:
            croise._live_step()
            vus.append(croise.flight["callsign"])
    changements = sum(1 for a, b in zip(vus, vus[1:]) if a != b)
    check("hysteresis : deux avions qui se croisent ne clignotent pas",
          changements == 0, " ".join(vus))

    # 22j. Veille nocturne : la luminosite suit l'heure
    veille = passerelle.Gateway({"luminosite_jour": 40, "luminosite_nuit": 8,
                                 "nuit_debut": 22, "nuit_fin": 7})

    def lum(h):
        return veille.luminosite(datetime.datetime(2026, 9, 20, h, 0))

    check("plein jour : luminosite normale", lum(14) == 40, str(lum(14)))
    check("22 h : la nuit commence", lum(22) == 8, str(lum(22)))
    check("3 h du matin : toujours la nuit", lum(3) == 8, str(lum(3)))
    check("7 h : le jour revient", lum(7) == 40, str(lum(7)))
    check("21 h : encore le jour", lum(21) == 40, str(lum(21)))

    # Une plage qui ne traverse pas minuit doit marcher aussi
    jour_seul = passerelle.Gateway({"luminosite_jour": 40, "luminosite_nuit": 8,
                                    "nuit_debut": 2, "nuit_fin": 5})
    check("plage de nuit sans passage par minuit",
          jour_seul.luminosite(datetime.datetime(2026, 9, 20, 3)) == 8
          and jour_seul.luminosite(datetime.datetime(2026, 9, 20, 23)) == 40)

    # Bornes egales : pas de nuit du tout, plutot qu'une nuit permanente
    sans_nuit = passerelle.Gateway({"luminosite_jour": 40, "nuit_debut": 0,
                                    "nuit_fin": 0})
    check("bornes egales : jamais de nuit",
          sans_nuit.luminosite(datetime.datetime(2026, 9, 20, 3)) == 40)

    # La nuit peut finir au Fajr plutot qu'a une heure fixe
    au_fajr = passerelle.Gateway({"luminosite_jour": 40, "luminosite_nuit": 8,
                                  "nuit_debut": 23, "nuit_fin": "fajr"})
    au_fajr.prieres = {"jour": [{"nom": "FAJR", "adhan": "05:55"}]}

    def lum_f(h, m=0):
        return au_fajr.luminosite(datetime.datetime(2026, 9, 20, h, m))

    check("22h59 : encore le jour", lum_f(22, 59) == 40)
    check("23h00 : la nuit commence", lum_f(23, 0) == 8)
    check("juste avant le fajr : encore la nuit", lum_f(5, 54) == 8)
    check("au fajr : le jour revient", lum_f(5, 55) == 40)
    check("apres le fajr : le jour", lum_f(8, 0) == 40)

    # Sans horaires, on ne doit pas rester bloque dans la nuit
    sans_horaires = passerelle.Gateway({"luminosite_jour": 40,
                                        "luminosite_nuit": 8,
                                        "nuit_debut": 23, "nuit_fin": "fajr"})
    check("fajr inconnu : repli sur une heure fixe",
          sans_horaires.luminosite(datetime.datetime(2026, 9, 20, 9, 0)) == 40)

    # Une borne peut aussi etre une heure precise
    precise = passerelle.Gateway({"luminosite_jour": 40, "luminosite_nuit": 8,
                                  "nuit_debut": "23:30", "nuit_fin": "06:15"})
    check("bornes en HH:MM",
          precise.luminosite(datetime.datetime(2026, 9, 20, 23, 29)) == 40
          and precise.luminosite(datetime.datetime(2026, 9, 20, 23, 31)) == 8
          and precise.luminosite(datetime.datetime(2026, 9, 20, 6, 16)) == 40)

    # Le simulateur montre la baisse relative, pas le rapport cyclique brut :
    # 40 sur 255 convient a un panneau LED, pas a l'image d'un moniteur
    check("simulateur a pleine intensite le jour",
          au_fajr.luminosite_relative(datetime.datetime(2026, 9, 20, 12)) == 255)
    check("simulateur tamise la nuit, dans le meme rapport",
          au_fajr.luminosite_relative(datetime.datetime(2026, 9, 20, 2)) == 51,
          str(au_fajr.luminosite_relative(datetime.datetime(2026, 9, 20, 2))))

    clair = ecran_heure.render(HEURE)
    vifs = sum(clair.buf)
    tamise = ecran_heure.render(HEURE).attenue(64)
    check("l'attenuation assombrit sans vider l'image",
          0 < sum(tamise.buf) < vifs,
          "%d contre %d" % (sum(tamise.buf), vifs))
    check("attenuation a 255 : image intacte",
          sum(ecran_heure.render(HEURE).attenue(255).buf) == vifs)
    check("attenuation a 0 : panneau eteint",
          sum(ecran_heure.render(HEURE).attenue(0).buf) == 0)

    # 22i. Le mode demo doit alimenter les cinq ecrans de la rotation,
    # sinon il ne sert plus a travailler la mise en page hors ligne
    demo = passerelle.Gateway({"demo_mode": True, "rotation_seconds": 30})
    demo._demo_step()
    ecran, vol_d, pri_d, met_d, heu_d, adk_d, usa_d = demo.screen()
    check("mode demo : un vol", vol_d is not None)
    check("mode demo : une priere", pri_d is not None)
    check("mode demo : la journee complete pour le tableau",
          len(pri_d.get("jour") or []) == 5)
    check("mode demo : une meteo", met_d is not None)
    check("mode demo : une heure", bool((heu_d or {}).get("heure")))
    check("mode demo : une entree adkar", adk_d is not None)
    # Un releve fictif : le quota ne vient pas du reseau, mais on veut
    # quand meme verifier que son ecran entre bien dans la rotation.
    usa_demo = {"cle_a": "5H", "restant_a": 61, "reset_a": "4H25",
                "cle_b": "7J", "restant_b": 52, "reset_b": "5J7H"}
    tours = set()
    for _ in range(16):
        demo.rotation_debut = 0  # force le passage au suivant
        tours.add(demo._rotation(vol_d, pri_d, met_d, adk_d, usa_demo))
    check("mode demo : les sept ecrans tournent",
          tours == {"vol", "priere", "horaires", "meteo", "adkar", "claude",
                    "heure"},
          " ".join(sorted(tours)))
    sans_usage = set()
    for _ in range(14):
        demo.rotation_debut = 0
        sans_usage.add(demo._rotation(vol_d, pri_d, met_d, adk_d, None))
    check("sans releve de quota, l'ecran Claude disparait de la rotation",
          "claude" not in sans_usage, " ".join(sorted(sans_usage)))

    # 22g. L'annonce meteo ne doit jamais manger le tour entier, sinon
    # l'ecran meteo lui-meme ne s'afficherait jamais
    for periode, attendu in ((30, ecran_alerte.ALERTE_MS), (2, 1000.0),
                             (1, 500.0)):
        g = passerelle.Gateway({"rotation_seconds": periode})
        check("annonce meteo bornee a %d s de rotation" % periode,
              g._duree_annonce_meteo() == attendu,
              "%.0f ms" % g._duree_annonce_meteo())

    # 24. Ecran adkar : un nom d'Allah par jour
    check("adkar : les 99 noms", adkar.combien() == 99,
          "%d entrees" % adkar.combien())
    check("adkar : pas de doublon dans les noms",
          len({e[1] for e in adkar.ENTREES}) == 99,
          "%d translitterations distinctes" % len({e[1]
                                                   for e in adkar.ENTREES}))
    check("adkar : tout est en ASCII, la police n'a rien d'autre",
          all("".join(e[1:]).isascii() for e in adkar.ENTREES))
    check("adkar : silhouette, translitteration, sens et signification",
          all(all(e[n] for n in range(4)) for e in adkar.ENTREES))

    # Chaque caractere doit exister dans la police, sans quoi il sortirait
    # en '?' sur le mur
    hors_police = sorted({c for e in adkar.ENTREES for c in "".join(e[1:])
                          if c not in font5x7.GLYPHS})
    check("adkar : aucun caractere hors de la police 5x7",
          not hors_police, "".join(hors_police) or "%d entrees relues"
          % adkar.combien())

    # Une silhouette plus large que le panneau serait rognee des deux cotes
    trop_large = [e[1] for e in adkar.ENTREES
                  if adkar.largeur(e[0]) > ecran_adkar.ADKAR_X1
                  - ecran_adkar.ADKAR_X0 + 1]
    check("adkar : aucune silhouette ne deborde du cadre",
          not trop_large, ", ".join(trop_large) if trop_large
          else "%d px au plus" % max(adkar.largeur(e[0])
                                     for e in adkar.ENTREES))
    check("adkar : silhouettes toutes a la hauteur annoncee",
          all(len(e[0]) == adkar.HAUTEUR for e in adkar.ENTREES))

    # La liste boucle : l'ecran ne doit jamais tomber sur un trou
    check("adkar : le rang boucle sur la liste",
          adkar.entree(adkar.combien()) == adkar.entree(0))
    check("adkar : un rang negatif reste dans la liste",
          adkar.entree(-1) == adkar.ENTREES[-1])

    # Le rang vient de la date seule : meme jour, meme nom des deux cotes,
    # sans etat a synchroniser, et le nom ne change pas en cours de journee
    adk = passerelle.Gateway({"duree_ecrans": tempos})
    matin = datetime.datetime(2026, 9, 20, 6, 30)
    soir = datetime.datetime(2026, 9, 20, 23, 30)
    lendemain = datetime.datetime(2026, 9, 21, 6, 30)
    check("adkar : le meme nom toute la journee",
          adk.current_adkar(matin) == adk.current_adkar(soir),
          "rang %s" % adk.current_adkar(matin))
    check("adkar : un nom different le lendemain",
          adk.current_adkar(matin) != adk.current_adkar(lendemain),
          "%s puis %s" % (adk.current_adkar(matin),
                          adk.current_adkar(lendemain)))
    check("adkar : le rang reste dans la liste",
          all(0 <= adk.current_adkar(matin + datetime.timedelta(days=n))
              < adkar.combien() for n in range(0, 400)))
    check("adkar : les 99 noms passent tous en 99 jours",
          len({adk.current_adkar(matin + datetime.timedelta(days=n))
               for n in range(99)}) == 99)

    # L'ecran doit rester assez longtemps pour un tour complet de la ligne :
    # une signification coupee en deux ne servirait a personne
    courts, tours = [], []
    for n in range(adkar.combien()):
        jour = matin + datetime.timedelta(days=n)
        entree = adkar.entree(adk.current_adkar(jour))
        tour = adk.duree_adkar(jour)
        tours.append(tour)
        if tour < ecran_adkar.duree_defilement(entree):
            courts.append(entree[1])
    check("adkar : le tour d'ecran couvre le defilement, quel que soit le jour",
          not courts, ", ".join(courts[:3]) if courts
          else "de %.0f a %.0f s selon le nom" % (min(tours), max(tours)))
    check("adkar : le tempo ne descend jamais sous le plancher de config",
          adk.duree_ecran("adkar") >= tempos["adkar"],
          "%.0f s" % adk.duree_ecran("adkar"))

    # Mise en page : en-tete, silhouette et ligne du bas tiennent dans 32 px
    bas_y = ecran_adkar.ADKAR_SENS_Y + font5x7.GLYPH_HEIGHT
    check("adkar : la ligne du bas tient dans la hauteur du panneau",
          bas_y <= panel.HEIGHT, "%d px" % bas_y)
    check("adkar : la silhouette ne recouvre ni l'en-tete ni le bas",
          ecran_adkar.ADKAR_MOT_Y >= ecran_adkar.ADKAR_ENTETE_Y
          + font5x7.GLYPH_HEIGHT
          and ecran_adkar.ADKAR_MOT_Y + adkar.HAUTEUR
          <= ecran_adkar.ADKAR_SENS_Y)

    # L'en-tete dit ou l'on en est, et doit laisser la place a l'heure
    check("adkar : l'en-tete numerote le nom du jour",
          ecran_adkar.entete(11) == "ADKAR 12/99", ecran_adkar.entete(11))
    place = (font5x7.text_width(ecran_adkar.entete(98))
             + font5x7.text_width("23:07") + 4)
    check("adkar : l'en-tete laisse la place a l'heure",
          place <= ecran_adkar.ADKAR_X1 - ecran_adkar.ADKAR_X0 + 1,
          "%d px" % place)

    # L'ecran doit dessiner quelque chose, et l'heure doit y figurer
    vue = ecran_adkar.render(0, 0.0, heure="23:07")
    check("adkar : l'ecran dessine", sum(vue.buf) > 0)
    sans_heure = ecran_adkar.render(0, 0.0)
    check("adkar : l'heure figure sur l'ecran, comme sur les autres",
          sum(vue.buf) > sum(sans_heure.buf))
    check("adkar : sans rang, on retombe sur la veille",
          sum(ecran_adkar.render(None, heure="23:07").buf) > 0)

    # La ligne du bas defile, et porte bien la signification detaillee
    bas = ecran_adkar.texte_bas(adkar.entree(0))
    check("adkar : la ligne du bas porte le nom, le sens et la signification",
          bas.count(" - ") >= 2 and len(bas) > 60, "%d caracteres" % len(bas))
    a = ecran_adkar.render(0, 0.0, heure="23:07")
    b = ecran_adkar.render(0, 1.0, heure="23:07")
    check("adkar : la signification defile", a.buf != b.buf)

    # 25. Le rang adkar voyage dans la charge utile, sinon les deux cotes
    # montreraient chacun un nom different
    charge = composition.compact_flight(None, None, "adkar", None, None, 42)
    check("charge utile : le rang adkar est transmis",
          charge.get("ad") == 42, str(charge.get("ad")))
    check("charge utile : pas de champ adkar quand il n'y en a pas",
          "ad" not in composition.compact_flight(None))
    check("charge utile : l'ecran adkar n'est pas une annonce",
          composition.ECRAN_DE_FOND.get("adkar", "adkar") == "adkar")

    # 26. Ecran Claude Code : l'etoile qui tourne et le quota restant
    check("etoile : huit phases carrees de 21 pixels",
          len(ecran_claude.ETOILE) == ecran_claude.CLAUDE_PHASES
          and all(len(m) == ecran_claude.CLAUDE_LOGO_PX
                  and all(len(l) == ecran_claude.CLAUDE_LOGO_PX for l in m)
                  for m in ecran_claude.ETOILE),
          "%d phases" % len(ecran_claude.ETOILE))
    check("etoile : chaque phase est differente de la suivante",
          all(ecran_claude.ETOILE[n] != ecran_claude.ETOILE[n + 1]
              for n in range(len(ecran_claude.ETOILE) - 1)))
    # La rotation boucle : onze branches, un onzieme de tour, retour au depart
    check("etoile : la rotation boucle sur elle-meme",
          ecran_claude.phase(0.0) == 0
          and ecran_claude.phase(ecran_claude.CLAUDE_PHASES
                                 / ecran_claude.CLAUDE_PHASES_PAR_SEC) == 0)
    check("etoile : l'animation passe toutes les phases en un tour",
          len({ecran_claude.phase(n / 24.0) for n in range(48)})
          == ecran_claude.CLAUDE_PHASES)
    check("etoile : le logo tient sous l'en-tete",
          ecran_claude.CLAUDE_LOGO_Y >= font5x7.GLYPH_HEIGHT
          and ecran_claude.CLAUDE_LOGO_Y + ecran_claude.CLAUDE_LOGO_PX
          <= panel.HEIGHT + 1,
          "y %d a %d" % (ecran_claude.CLAUDE_LOGO_Y,
                         ecran_claude.CLAUDE_LOGO_Y
                         + ecran_claude.CLAUDE_LOGO_PX - 1))
    check("etoile : le logo ne mord pas sur les libelles",
          ecran_claude.CLAUDE_LOGO_X + ecran_claude.CLAUDE_LOGO_PX
          <= ecran_claude.CLAUDE_CLE_X)

    # Les trois blocs d'une ligne ne doivent pas se chevaucher
    fin_cle = ecran_claude.CLAUDE_CLE_X + font5x7.text_width("5H")
    check("jauge : libelle, barre, pourcentage et echeance s'enchainent",
          fin_cle < ecran_claude.CLAUDE_BARRE_X0
          and ecran_claude.CLAUDE_BARRE_X1 < ecran_claude.CLAUDE_PCT_X1
          - font5x7.text_width("100%")
          and ecran_claude.CLAUDE_PCT_X1 < ecran_claude.CLAUDE_X1
          - font5x7.text_width("5J6H"))

    # Lecture d'usage.json : le fichier fait foi, l'horloge fait le reste
    releve = datetime.datetime(2026, 9, 20, 12, 0)
    brut = {"plan": "Pro", "releve": releve.isoformat(),
            "fenetres": [{"cle": "5H", "utilise": 39,
                          "reset": (releve
                                    + datetime.timedelta(hours=4,
                                                         minutes=25)).isoformat()},
                         {"cle": "7J", "utilise": 48,
                          "reset": (releve
                                    + datetime.timedelta(days=5,
                                                         hours=7)).isoformat()}]}
    dossier = tempfile.mkdtemp()
    chemin_usage = os.path.join(dossier, "usage.json")
    with open(chemin_usage, "w", encoding="utf-8") as handle:
        json.dump(brut, handle)

    lu = claudesource.poll({}, chemin_usage, releve)
    check("quota : la jauge montre ce qui RESTE, pas ce qui est consomme",
          lu["restant_a"] == 61 and lu["restant_b"] == 52,
          "%s et %s" % (lu["restant_a"], lu["restant_b"]))
    check("quota : les libelles viennent du fichier",
          (lu["cle_a"], lu["cle_b"]) == ("5H", "7J"))
    check("quota : les echeances tiennent en quatre caracteres",
          lu["reset_a"] == "4H25" and lu["reset_b"] == "5J7H",
          "%s et %s" % (lu["reset_a"], lu["reset_b"]))

    # Toutes les formes d'echeance doivent rester courtes, sans quoi elles
    # deborderaient sur le pourcentage
    longues = []
    for minutes in (1, 59, 60, 61, 599, 600, 1439, 1440, 1441,
                    14399, 14400, 100000):
        texte = claudesource.format_reste(
            releve + datetime.timedelta(minutes=minutes), releve)
        if len(texte) > 4:
            longues.append("%d -> %s" % (minutes, texte))
    check("quota : aucune echeance ne depasse quatre caracteres",
          not longues, "; ".join(longues) or "douze formes essayees")

    # Une fenetre dont l'heure est passee devient inconnue, pas nulle
    apres = releve + datetime.timedelta(hours=5)
    tard = claudesource.poll({}, chemin_usage, apres)
    check("quota : une fenetre expiree devient inconnue, et non nulle",
          tard["restant_a"] is None and tard["restant_b"] == 52,
          str(tard["restant_a"]))
    check("quota : une fenetre expiree n'affiche plus d'echeance",
          tard["reset_a"] == "")

    # Un releve trop vieux fait disparaitre l'ecran plutot que de mentir
    vieux = releve + datetime.timedelta(hours=30)
    check("quota : un releve perime fait disparaitre l'ecran",
          claudesource.poll({}, chemin_usage, vieux) is None)
    check("quota : la peremption est reglable",
          claudesource.poll({"usage_age_max_heures": 48}, chemin_usage,
                            vieux) is not None)
    check("quota : pas de fichier, pas d'ecran",
          claudesource.poll({}, os.path.join(dossier, "absent.json"),
                            releve) is None)
    with open(chemin_usage, "w", encoding="utf-8") as handle:
        handle.write("{ceci n'est pas du json")
    check("quota : un fichier illisible ne fait pas tomber la passerelle",
          claudesource.poll({}, chemin_usage, releve) is None)

    # La jauge change de couleur quand la reserve fond
    check("jauge : verte tant qu'il en reste",
          ecran_claude.couleur_jauge(61) == panel.ACCENT)
    check("jauge : orange sous le seuil",
          ecran_claude.couleur_jauge(ecran_claude.CLAUDE_SEUIL_BAS)
          == panel.TEXTE)
    check("jauge : eteinte quand on ne sait pas",
          ecran_claude.couleur_jauge(None) == panel.SEP)

    # Le rendu lui-meme
    vue_cc = ecran_claude.render(lu, 0.0, heure="13:59")
    check("claude : l'ecran dessine", sum(vue_cc.buf) > 0)
    check("claude : l'heure figure sur l'ecran, comme sur les autres",
          sum(vue_cc.buf) > sum(ecran_claude.render(lu, 0.0).buf))
    check("claude : l'etoile tourne d'une image a l'autre",
          vue_cc.buf != ecran_claude.render(lu, 1.0 / 6.0,
                                            heure="13:59").buf)
    check("claude : sans releve, on retombe sur la veille",
          sum(ecran_claude.render(None, heure="13:59").buf) > 0)

    # Le pourcentage a besoin du glyphe correspondant, sinon il sort en '?'
    check("police : le glyphe pourcent existe", "%" in font5x7.GLYPHS)

    # 27. Le quota voyage dans la charge utile
    charge_cc = composition.compact_flight(None, None, "claude", None, None,
                                           None, lu)
    check("charge utile : le quota est transmis",
          charge_cc["cl"]["ra"] == 61 and charge_cc["cl"]["ta"] == "4H25",
          json.dumps(charge_cc["cl"]))
    check("charge utile : une fenetre inconnue part a -1",
          composition.compact_flight(None, None, "claude", None, None, None,
                                     tard)["cl"]["ra"] == -1)
    check("charge utile : pas de champ quota quand il n'y en a pas",
          "cl" not in composition.compact_flight(None))

    # 28. Annonces de la mosquee : lues dans le confData deja en cache
    CONF_ANNONCES = {
        "announcements": [
            {"title": "Conference Vendredi 20h"},
            {"title": "Cours d'arabe"},
            {"title": "Termine", "endDate": "2020-01-01 10:00"},
            {"title": "Plus tard", "startDate": "2099-01-01 10:00"},
        ],
    }
    maintenant = datetime.datetime(2026, 9, 20, 12, 0)
    titres = annonces.liste(CONF_ANNONCES, maintenant)
    check("annonces : seules celles en cours sont retenues",
          titres == ("CONFERENCE VENDREDI 20H", "COURS D'ARABE"),
          " | ".join(titres))
    check("annonces : une annonce sans dates est permanente",
          annonces.en_cours({"title": "x"}, maintenant))
    check("annonces : les accents passent par la police, pas par des '?'",
          "?" not in annonces.propre("Conference a la mosquee"),
          annonces.propre("Conference a la mosquee"))
    check("annonces : un titre a rallonge est tronque",
          len(annonces.propre("A" * 200)) == annonces.LONGUEUR_MAX,
          "%d caracteres" % len(annonces.propre("A" * 200)))
    beaucoup = {"announcements": [{"title": "TITRE %d" % n}
                                  for n in range(9)]}
    check("annonces : jamais plus de COMBIEN_MAX titres",
          len(annonces.liste(beaucoup, maintenant)) == annonces.COMBIEN_MAX,
          "%d titres" % len(annonces.liste(beaucoup, maintenant)))
    check("annonces : pas d'annonce, pas de liste",
          annonces.liste({}, maintenant) == ()
          and annonces.liste(None, maintenant) == ())

    # L'ecran, et son tempo qui s'adapte a la longueur du bandeau
    tour = ecran_annonces.duree_tour(titres)
    check("annonces : le bandeau fait un tour en un temps raisonnable",
          10 <= tour <= 60, "%.0f s" % tour)
    info_an = {"mosquee": "MOSQUEE", "heure": "23:07", "annonces": titres}
    vue_an = ecran_annonces.render(info_an, 0.0)
    check("annonces : l'ecran dessine", sum(vue_an.buf) > 0)
    check("annonces : le bandeau defile",
          vue_an.buf != ecran_annonces.render(info_an, 2.0).buf)
    check("annonces : sans annonce, on retombe sur la veille",
          sum(ecran_annonces.render({"mosquee": "MOSQUEE", "heure": "23:07"},
                                    0.0).buf) > 0)

    an_gw = passerelle.Gateway({"duree_ecrans": tempos})
    an_gw.prieres = dict(info, annonces=titres)
    check("annonces : le tour d'ecran couvre le bandeau",
          an_gw.duree_ecran("annonces") >= tour,
          "%.0f s pour %.0f s de bandeau"
          % (an_gw.duree_ecran("annonces"), tour))
    avec = set()
    sans = set()
    for _ in range(10):
        an_gw.rotation_debut = 0
        avec.add(an_gw._rotation(None, dict(info, annonces=titres), None))
    an_gw.prieres = dict(info, annonces=())
    for _ in range(10):
        an_gw.rotation_debut = 0
        sans.add(an_gw._rotation(None, dict(info, annonces=()), None))
    check("annonces : l'ecran n'existe que si la mosquee publie",
          "annonces" in avec and "annonces" not in sans,
          "avec %s / sans %s" % (" ".join(sorted(avec)),
                                 " ".join(sorted(sans))))
    an_gw.prieres = dict(info, annonces=titres)
    charge_an = composition.compact_flight(None, dict(info, annonces=titres),
                                           "annonces")
    check("charge utile : les titres partent separes par une barre",
          charge_an["pr"]["an"] == composition.SEP_ANNONCES.join(titres),
          charge_an["pr"]["an"])
    check("charge utile : pas de titres, champ vide",
          composition.compact_flight(None, info, "priere")["pr"]["an"] == "")

    # 29. Pluie a venir : lue dans la prevision au quart d'heure
    quarts = {
        "time": [(maintenant + datetime.timedelta(minutes=15 * n)).isoformat()
                 for n in range(8)],
        "precipitation": [0.0, 0.0, 0.05, 0.6, 1.2, 0.0, 0.0, 0.0],
    }
    minutes, heure_pluie = meteosource.prochaine_pluie(quarts, maintenant)
    check("pluie : la premiere averse au-dessus du seuil est retenue",
          minutes == 45, str(minutes))
    check("pluie : son heure de debut accompagne le delai",
          heure_pluie == "12:45", heure_pluie)
    check("pluie : trois gouttes ne declenchent rien",
          meteosource.prochaine_pluie(quarts, maintenant, seuil=2.0)[0] is None)
    check("pluie : au-dela de l'horizon, on ne previent pas",
          meteosource.prochaine_pluie(quarts, maintenant,
                                      horizon=30)[0] is None)
    check("pluie : pas de prevision, pas d'alerte",
          meteosource.prochaine_pluie({}, maintenant)[0] is None
          and meteosource.prochaine_pluie(None, maintenant)[0] is None)

    # Les deux formes du texte, et leur place sur la ligne du bas
    proche = {"pluie_min": 40, "pluie_heure": "17:30"}
    loin = {"pluie_min": 95, "pluie_heure": "18:25"}
    check("pluie : sous l'heure, un decompte en minutes",
          ecran_meteo.texte_pluie(proche) == "PLUIE 40 MIN",
          ecran_meteo.texte_pluie(proche))
    check("pluie : au-dela, l'heure de debut",
          ecran_meteo.texte_pluie(loin) == "PLUIE 18:25",
          ecran_meteo.texte_pluie(loin))
    check("pluie : rien a dire quand il n'en vient pas",
          ecran_meteo.texte_pluie({"pluie_min": None}) == "")
    large_pluie = max(font5x7.text_width(ecran_meteo.texte_pluie(
        {"pluie_min": n, "pluie_heure": "18:25"})) for n in range(0, 121))
    place_vent = (ecran_meteo.METEO_X1 - font5x7.text_width("199 KM/H")
                  - ecran_meteo.METEO_X0 - 2)
    check("pluie : l'alerte ne mord pas sur le vent",
          large_pluie <= place_vent,
          "%d px pour %d" % (large_pluie, place_vent))
    check("pluie : l'annonce tient dans la largeur du panneau",
          font5x7.text_width(ecran_meteo.annonce_pluie(loin)) <= panel.WIDTH,
          ecran_meteo.annonce_pluie(loin))

    # Une averse en cours ne s'annonce pas : l'icone le dit deja
    meteo_pluie = dict(METEO, pluie_min=40, pluie_heure="17:30")
    vue_pl = ecran_meteo.render(meteo_pluie)
    check("pluie : l'alerte prend la place du lieu sur la ligne du bas",
          vue_pl.buf != ecran_meteo.render(METEO).buf)
    charge_pl = composition.compact_flight(None, None, "meteo", meteo_pluie)
    check("charge utile : la pluie est transmise",
          charge_pl["mt"]["pm"] == 40 and charge_pl["mt"]["ph"] == "17:30")
    check("charge utile : pas de pluie, champ a -1",
          composition.compact_flight(None, None, "meteo",
                                     METEO)["mt"]["pm"] == -1)

    # 30. Liaison perdue : le firmware l'impose contre le champ "sc"
    check("liaison : un silence court ne declenche rien",
          not ecran_liaison.perdue(ecran_liaison.LIAISON_SEUIL_MS - 1))
    check("liaison : au seuil, le panneau retire sa confiance",
          ecran_liaison.perdue(ecran_liaison.LIAISON_SEUIL_MS))
    check("liaison : sans mesure, on ne declenche pas",
          not ecran_liaison.perdue(None))
    check("liaison : le seuil laisse passer plusieurs polls manques",
          ecran_liaison.LIAISON_SEUIL_MS >= 60000,
          "%d ms" % ecran_liaison.LIAISON_SEUIL_MS)
    check("liaison : la duree se dit en minutes puis en heures",
          ecran_liaison.format_depuis(4 * 60000) == "DEPUIS 4 MIN"
          and ecran_liaison.format_depuis(150 * 60000) == "DEPUIS 2H",
          ecran_liaison.format_depuis(150 * 60000))
    trop_larges = [t for t in (ecran_liaison.TITRE, ecran_liaison.SOUS_TITRE,
                               ecran_liaison.format_depuis(999 * 60000))
                   if font5x7.text_width(t) > panel.WIDTH]
    check("liaison : les trois lignes tiennent dans la largeur",
          not trop_larges, ", ".join(trop_larges) or "trois lignes centrees")
    vue_li = ecran_liaison.render(4 * 60000)
    check("liaison : l'ecran dessine", sum(vue_li.buf) > 0)
    check("liaison : l'ecran ne porte pas d'heure, justement",
          "liaison" not in composition.ECRAN_DE_FOND
          and "liaison" in composition.ECRANS_LOCAUX)

    # 31. Audio : l'adhan et l'iqama, decides par la passerelle
    CFG_AUDIO = {"audio_actif": True, "volume_jour": 22, "volume_nuit": 12}

    def priere_phase(phase, nom="MAGHREB"):
        return {"nom": nom, "phase": phase, "demain": False}

    # Le nom des phases dit ce qui vient de se passer, pas ce qu'on attend :
    # l'adhan retentit a l'entree en phase "iqama".
    check("audio : rien avant l'adhan",
          audio.son(priere_phase("adhan"), CFG_AUDIO) == audio.SON_AUCUN)
    check("audio : l'adhan part quand son heure est passee",
          audio.son(priere_phase("iqama"), CFG_AUDIO) == audio.SON_ADHAN)
    check("audio : l'iqama a son signal court",
          audio.son(priere_phase("encours"), CFG_AUDIO) == audio.SON_IQAMA)
    check("audio : les cinq prieres sonnent, sans exception",
          all(audio.son(priere_phase("iqama", nom), CFG_AUDIO)
              == audio.SON_ADHAN
              for nom in ("FAJR", "DOHR", "ASR", "MAGHREB", "ICHA")))
    check("audio : le fajr de demain ne sonne pas",
          audio.son(dict(priere_phase("iqama", "FAJR"), demain=True),
                    CFG_AUDIO) == audio.SON_AUCUN)
    check("audio : la coupure fait taire le panneau",
          audio.son(priere_phase("iqama"),
                    dict(CFG_AUDIO, audio_actif=False)) == audio.SON_AUCUN)
    check("audio : pas de priere, pas de son",
          audio.son(None, CFG_AUDIO) == audio.SON_AUCUN)

    # La cle d'unicite : c'est elle qui evite qu'un son se rejoue toutes les
    # trois secondes, a chaque interrogation de la passerelle
    check("audio : la cle ne bouge pas tant que la phase dure",
          audio.cue(priere_phase("iqama")) == audio.cue(priere_phase("iqama")),
          audio.cue(priere_phase("iqama")))
    check("audio : la cle change au passage de phase",
          audio.cue(priere_phase("iqama"))
          != audio.cue(priere_phase("encours")))
    check("audio : la cle change d'une priere a l'autre",
          audio.cue(priere_phase("iqama", "DOHR"))
          != audio.cue(priere_phase("iqama", "ASR")))
    check("audio : pas de cle quand il n'y a rien a jouer",
          audio.cue(priere_phase("adhan")) == "" and audio.cue(None) == "")
    check("audio : la cle tient dans le champ du firmware",
          all(len(audio.cue(priere_phase(ph, nom))) < 24
              for ph in ("iqama", "encours")
              for nom in ("FAJR", "DOHR", "ASR", "MAGHREB", "ICHA",
                          "JOUMOUA")),
          "%d caracteres au plus"
          % max(len(audio.cue(priere_phase(ph, nom)))
                for ph in ("iqama", "encours")
                for nom in ("FAJR", "DOHR", "ASR", "MAGHREB", "ICHA",
                            "JOUMOUA")))

    # Le volume suit la meme nuit que la luminosite
    check("audio : volume du jour", audio.volume(CFG_AUDIO, False) == 22)
    check("audio : volume de nuit", audio.volume(CFG_AUDIO, True) == 12)
    check("audio : le volume reste dans la plage du DFPlayer",
          audio.volume({"volume_jour": 99}, False) == audio.VOLUME_MAX
          and audio.volume({"volume_jour": -5}, False) == 0)
    check("audio : un volume illisible retombe sur le defaut",
          audio.volume({"volume_jour": "fort"}, False) == audio.VOLUME_JOUR)
    check("audio : la nuit est plus discrete que le jour",
          audio.VOLUME_NUIT < audio.VOLUME_JOUR)

    # Une seule definition de la nuit pour la luminosite et le volume
    nuit_gw = passerelle.Gateway({"nuit_debut": 23, "nuit_fin": 7,
                                  "luminosite_jour": 40, "luminosite_nuit": 8,
                                  "volume_jour": 22, "volume_nuit": 12})
    for heure_test, attendu in ((14, False), (23, True), (3, True),
                                (7, False)):
        quand = datetime.datetime(2026, 9, 20, heure_test, 0)
        coherent = (nuit_gw.de_nuit(quand) == attendu
                    and (nuit_gw.luminosite(quand) == 8) == attendu)
        check("audio : a %dh, luminosite et volume voient la meme nuit"
              % heure_test, coherent, "de_nuit=%s" % nuit_gw.de_nuit(quand))

    etat_nuit = nuit_gw.current_audio(datetime.datetime(2026, 9, 20, 3, 0))
    check("audio : la passerelle baisse le volume la nuit",
          etat_nuit["volume"] == 12, str(etat_nuit["volume"]))

    # Le test qui compte vraiment : pas le nom des phases, mais l'heure a
    # laquelle le salon entend l'adhan. On parcourt la journee minute par
    # minute et on releve ce qui sonne, puis on compare aux horaires.
    jour_test = datetime.date(2026, 9, 19)
    attendu_adhan, attendu_iqama = {}, {}
    for priere in horaires.day_times(MAWAQIT_SAMPLE, jour_test)[0]:
        attendu_adhan[horaires._hhmm(priere["adhan"])] = priere["nom"]
        attendu_iqama[horaires._hhmm(priere["iqama"])] = priere["nom"]

    sonne_adhan, sonne_iqama = {}, {}
    cue_precedente = None
    for minute in range(24 * 60):
        quand = datetime.datetime.combine(
            jour_test, datetime.time(minute // 60, minute % 60))
        courante = horaires.next_prayer(MAWAQIT_SAMPLE, quand)
        etat_m = audio.etat(courante, CFG_AUDIO, False)
        if etat_m["cue"] and etat_m["cue"] != cue_precedente:
            registre = (sonne_adhan if etat_m["son"] == audio.SON_ADHAN
                        else sonne_iqama)
            registre[quand.strftime("%H:%M")] = courante["nom"]
        cue_precedente = etat_m["cue"]

    check("audio : l'adhan retentit a l'heure de la priere, aux cinq",
          sonne_adhan == attendu_adhan,
          " ".join("%s %s" % (h, n) for h, n in sorted(sonne_adhan.items())))
    check("audio : l'iqama sonne quand la priere commence, aux cinq",
          sonne_iqama == attendu_iqama,
          " ".join("%s %s" % (h, n) for h, n in sorted(sonne_iqama.items())))
    check("audio : rien ne sonne en dehors de ces dix moments",
          len(sonne_adhan) + len(sonne_iqama) == 10,
          "%d declenchements" % (len(sonne_adhan) + len(sonne_iqama)))

    # La priere courante doit etre recalculee a la demande, sans quoi l'adhan
    # retentirait jusqu'a un tour de boucle apres l'heure de la mosquee
    ponctuel = passerelle.Gateway({"mosquee_slug": "test"})
    ponctuel.conf = MAWAQIT_SAMPLE
    ponctuel.prieres = {"nom": "PERIME", "phase": "adhan"}
    avant = ponctuel.current_prieres(
        datetime.datetime.combine(jour_test, datetime.time(19, 58)))
    apres = ponctuel.current_prieres(
        datetime.datetime.combine(jour_test, datetime.time(20, 0)))
    check("audio : la priere se recalcule a la demande, pas au sondage",
          avant["phase"] != apres["phase"]
          and avant["nom"] != "PERIME",
          "%s puis %s" % (avant["phase"], apres["phase"]))

    # La charge utile porte le son, sa cle et le volume
    etat_son = audio.etat(priere_phase("iqama"), CFG_AUDIO, False)
    charge_son = composition.compact_flight(None, None, "priere", None, None,
                                            None, None, etat_son)
    check("charge utile : le son et sa cle sont transmis",
          charge_son["au"]["s"] == audio.SON_ADHAN
          and charge_son["au"]["c"] == "MAGHREB:iqama",
          json.dumps(charge_son["au"]))
    check("charge utile : le volume part meme sans rien a jouer",
          composition.compact_flight(
              None, None, "priere", None, None, None, None,
              audio.etat(priere_phase("adhan"), CFG_AUDIO))["au"]["v"] == 22)
    check("charge utile : pas de bloc audio quand la passerelle n'en envoie pas",
          "au" not in composition.compact_flight(None))

    # 22d. Regle du jumeau, verifiee dans son propre module
    verif_jumeau.verifie(check)

    # 22p. Robustesse : delais stricts, un fil par source, caches surs
    verif_robustesse.verifie(check)

    # 22o. Regles du croquis : reseau sur le Core 0, double tampon, secrets
    verif_croquis.verifie(check)

    # 22n. Annonce d'avion : meme comportement des deux cotes, verifie en
    # compilant firmware/annonce_vol.h (ignore sans compilateur C++)
    if not verif_annonce.verifie(check):
        print("compilateur C++ introuvable : annonce d'avion non comparee")

    # 23. Le cache des logos distingue les dossiers
    panel._LOGO_CACHE.clear()
    panel._LOGO_CACHE[("dossier_a", "AFR")] = "image_a"
    check("cache des logos indexe sur le dossier",
          panel._load_logo("AFR", "dossier_b") is None)
    panel._LOGO_CACHE.clear()

    largeur = max(len(label) for label, _, _ in checks)
    ok = True
    for label, passed, detail in checks:
        mark = "OK  " if passed else "ECHEC"
        print("%s  %-*s  %s" % (mark, largeur, label, detail))
        ok = ok and passed
    print("\n%d/%d verifications passees" % (sum(1 for _, p, _ in checks if p),
                                             len(checks)))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
