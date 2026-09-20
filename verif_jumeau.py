"""Verification de la regle du jumeau : Python et C doivent coincider.

Lit les en-tetes du firmware et compare chaque constante partagee, les
couleurs, les silhouettes et les textes d'annonce a leurs jumelles Python.
Une divergence echoue en nommant la constante fautive.

C'est la seule garantie automatique que le depot tient sa promesse : sans
elle, les deux moities derivent en silence.
"""

import os
import re

import adkar
import arabe
import audio
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
import panel
import transitions

FIRMWARE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firmware")


def constante_c(fichier, nom):
    """Valeur d'une constante dans un fichier C, ou None."""
    with open(os.path.join(FIRMWARE, fichier), encoding="ascii") as handle:
        texte = handle.read()
    trouve = re.search(r"\b%s\s*=\s*([^,;]+)" % re.escape(nom), texte)
    return trouve.group(1).strip().rstrip("f") if trouve else None


def verifie(check):
    """Lance toutes les comparaisons, en passant par le 'check' du test."""
    # 22d. Regle du jumeau : les constantes partagees doivent coincider
    JUMELLES = [
        ("panneau_vols.ino", panel, ("LOGO_X0", "LOGO_X1", "SEP_X", "TEXT_X0",
                                     "LINE1_Y", "LINE2_Y", "LINE3_Y",
                                     "SCROLL_GAP", "SCROLL_PX_PER_SEC")),
        ("ecran_prieres.h", ecran_prieres, ("PRIERE_X0", "PRIERE_RULE_Y")),
        ("ecran_horaires.h", ecran_horaires,
         ("HORAIRES_X0", "HORAIRES_BANDE_Y", "HORAIRES_LATIN_DY",
          "HORAIRES_ECHELLE", "HORAIRES_GAP", "HORAIRES_ENTRE",
          "HORAIRES_PX_PAR_SEC")),
        ("ecran_annonces.h", ecran_annonces,
         ("ANNONCES_X0", "ANNONCES_BANDE_Y", "ANNONCES_ECHELLE",
          "ANNONCES_ENTRE", "ANNONCES_PX_PAR_SEC")),
        ("ecran_liaison.h", ecran_liaison,
         (("LIAISON_SEUIL_MS", "LIAISON_SEUIL_MS"),)),
        ("audio.h", audio, ("SON_AUCUN", "SON_ADHAN", "SON_IQAMA",
                            "VOLUME_MAX", "VOLUME_JOUR", "VOLUME_NUIT")),
        ("arabe.h", arabe, (("ARABE_H_PX", "HAUTEUR"),)),
        ("ecran_adkar.h", ecran_adkar,
         ("ADKAR_X0", "ADKAR_ENTETE_Y", "ADKAR_MOT_Y", "ADKAR_SENS_Y",
          "ADKAR_PX_PAR_SEC", "ADKAR_GAP")),
        ("adkar.h", adkar, (("ADKAR_H_PX", "HAUTEUR"),)),
        ("ecran_claude.h", ecran_claude,
         ("CLAUDE_X0", "CLAUDE_ENTETE_Y", "CLAUDE_LOGO_X", "CLAUDE_LOGO_Y",
          "CLAUDE_LIGNE1_Y", "CLAUDE_LIGNE2_Y", "CLAUDE_CLE_X",
          "CLAUDE_BARRE_X0", "CLAUDE_BARRE_X1", "CLAUDE_BARRE_DY",
          "CLAUDE_BARRE_H", "CLAUDE_PCT_X1", "CLAUDE_PHASES",
          "CLAUDE_LOGO_PX", "CLAUDE_PHASES_PAR_SEC", "CLAUDE_SEUIL_BAS")),
        ("ecran_meteo.h", ecran_meteo, ("METEO_X0", "METEO_ICONE_Y",
                                        "METEO_TEXTE_X")),
        ("ecran_heure.h", ecran_heure, ("HEURE_ECHELLE", "HEURE_Y", "DATE_Y")),
        ("icones_meteo.h", icones_meteo, (("ICONE_W", "LARGEUR"),
                                          ("ICONE_H", "HAUTEUR"))),
        ("transitions.h", transitions, ("TRANSITION_MS",)),
        ("ecran_alerte.h", ecran_alerte, ("ALERTE_MS", "AVION_Y", "AVION_W",
                                          "AVION_H", "MOSQUEE_Y", "MOSQUEE_W",
                                          "MOSQUEE_H")),
    ]
    ecarts, comparees = [], 0
    for fichier, module, noms in JUMELLES:
        for nom in noms:
            # un couple quand les deux cotes ne nomment pas la constante
            # pareil, une simple chaine sinon
            nom_c, nom_py = nom if isinstance(nom, tuple) else (nom, nom)
            comparees += 1
            c = constante_c(fichier, nom_c)
            py = getattr(module, nom_py)
            if c is None or abs(float(c) - float(py)) > 1e-6:
                ecarts.append("%s:%s c=%s py=%s" % (fichier, nom_c, c, py))
    check("constantes de mise en page identiques des deux cotes",
          not ecarts,
          "; ".join(ecarts) if ecarts else "%d constantes" % comparees)

    # Les couleurs, en 0xRRGGBB cote C
    ecarts_couleur = []
    for nom in ("TEXTE", "SECONDAIRE", "ACCENT", "PRINCIPAL", "SEP"):
        brut = constante_c("panneau_vols.ino", "RGB_" + nom)
        attendu = "0x%02X%02X%02X" % getattr(panel, nom)
        if brut != attendu:
            ecarts_couleur.append("%s c=%s py=%s" % (nom, brut, attendu))
    check("couleurs identiques des deux cotes",
          not ecarts_couleur,
          "; ".join(ecarts_couleur) if ecarts_couleur else "5 couleurs")

    # Les silhouettes, motif par motif, dans l'ordre du fichier
    def motifs(fichier):
        with open(os.path.join(FIRMWARE, fichier), encoding="ascii") as handle:
            return re.findall(r'"([.#]{5,})"', handle.read())

    etoile_attendue = []
    for motif in ecran_claude.ETOILE:
        etoile_attendue += list(motif)
    check("etoile Claude identique des deux cotes",
          motifs("ecran_claude.h") == etoile_attendue,
          "%d phases, %d lignes" % (len(ecran_claude.ETOILE),
                                    len(etoile_attendue)))

    attendus = list(ecran_alerte.AVION) + list(ecran_alerte.MOSQUEE)
    check("silhouettes identiques des deux cotes",
          motifs("ecran_alerte.h") == attendus,
          "%d lignes" % len(motifs("ecran_alerte.h")))

    # Les sept icones meteo, dans l'ordre d'icones_meteo.ORDRE
    icones_attendues = []
    for nom in icones_meteo.ORDRE:
        icones_attendues += list(icones_meteo.icone(nom))
    check("icones meteo identiques des deux cotes",
          motifs("icones_meteo.h") == icones_attendues,
          "%d icones, %d lignes" % (len(icones_meteo.ORDRE),
                                    len(icones_attendues)))

    # Les trois annonces, texte compris
    # nom partage, ou couple (nom C, nom Python) quand ils different
    for fichier, module, nom in (("ecran_alerte.h", ecran_alerte, "ANNONCE"),
                                 ("ecran_alerte.h", ecran_alerte,
                                  "ANNONCE_PRIERE"),
                                 ("ecran_meteo.h", ecran_meteo,
                                  "ANNONCE_METEO"),
                                 ("ecran_adkar.h", ecran_adkar,
                                  ("ADKAR_TITRE", "TITRE")),
                                 ("ecran_claude.h", ecran_claude,
                                  ("CLAUDE_TITRE", "TITRE")),
                                 ("ecran_claude.h", ecran_claude,
                                  ("CLAUDE_INCONNU", "INCONNU")),
                                 ("ecran_meteo.h", ecran_meteo,
                                  "ANNONCE_PLUIE"),
                                 ("ecran_annonces.h", ecran_annonces,
                                  ("ANNONCES_SEPARATEUR", "SEPARATEUR")),
                                 ("ecran_liaison.h", ecran_liaison,
                                  ("LIAISON_TITRE", "TITRE")),
                                 ("ecran_liaison.h", ecran_liaison,
                                  ("LIAISON_SOUS_TITRE", "SOUS_TITRE")),
                                 ("ecran_liaison.h", ecran_liaison,
                                  ("LIAISON_DEPUIS", "DEPUIS"))):
        nom_c, nom_py = nom if isinstance(nom, tuple) else (nom, nom)
        c = constante_c(fichier, nom_c)
        py = '"%s"' % getattr(module, nom_py)
        check("texte %s identique des deux cotes" % nom_c, c == py,
              "%s vs %s" % (c, py))
