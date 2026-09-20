"""Ecran des vols : indicatif, route, compagnie, logo.

Le tampon de pixels et les primitives de dessin sont dans cadre.py ; ce
fichier n'a plus que la mise en page de l'ecran des vols, jumelle de
renderFlight() dans firmware/ecran_vol.h.

Les noms de cadre.py sont reexportes ici, car tout le depot ecrit
panel.Frame, panel.WIDTH ou panel.TEXTE depuis le debut.
"""

import os
import time

import font5x7
from font5x7 import ADVANCE, ARROW, GLYPH_HEIGHT, PLANE

from cadre import (ACCENT, Frame, HEIGHT, PRINCIPAL, SECONDAIRE, SEP, TEXTE,
                   WIDTH, centre, droite)

# Zone logo a gauche, zone texte a droite
LOGO_X0, LOGO_X1 = 0, 29
LOGO_PX = 24      # cote du bitmap de compagnie, pose en (3, 4)
LOGO_MIN_PX = 10  # en deca, le logo est illisible : on prefere le code OACI
SEP_X = 31
TEXT_X0, TEXT_X1 = 34, WIDTH - 2  # une colonne de marge a droite
TEXT_W = TEXT_X1 - TEXT_X0 + 1

LINE1_Y = 1
LINE2_Y = 12
LINE3_Y = 23

SCROLL_PX_PER_SEC = 14.0
SCROLL_GAP = 12  # pixels de vide entre deux passages du texte defilant

_LOGO_CACHE = {}


def _fit(text, max_chars):
    text = (text or "").upper()
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _load_logo(icao, logo_dir):
    """Charge logos/<ICAO>.png en 24x24 si Pillow est installe, sinon None.

    Rapport largeur/hauteur conserve et image centree : beaucoup de logos sont
    des pavillons tres larges, qu'un redimensionnement brutal ecraserait.
    export_logos.py passe par cette meme fonction pour fabriquer les bitmaps de
    l'ESP32, ce qui garantit une image identique des deux cotes du jumeau.
    """
    if not icao:
        return None
    # le dossier fait partie de la cle : deux appels sur des dossiers
    # differents ne doivent pas se renvoyer la meme image
    key = (logo_dir, icao.upper())
    if key in _LOGO_CACHE:
        return _LOGO_CACHE[key]
    path = os.path.join(logo_dir, key[1] + ".png")
    bitmap = None
    if os.path.exists(path):
        try:
            from PIL import Image
            img = Image.open(path).convert("RGBA")
            img.thumbnail((LOGO_PX, LOGO_PX), Image.LANCZOS)
            if min(img.width, img.height) < LOGO_MIN_PX:
                # pavillon trop allonge : reduit a quelques pixels de haut il
                # ne serait qu'une trainee. Le repli texte est plus lisible.
                _LOGO_CACHE[key] = None
                return None
            carre = Image.new("RGBA", (LOGO_PX, LOGO_PX), (0, 0, 0, 0))
            carre.paste(img, ((LOGO_PX - img.width) // 2,
                              (LOGO_PX - img.height) // 2))
            # transparent -> noir, non dessine ; noir visible -> presque noir,
            # sinon il disparaitrait avec le fond
            pixels = [(0, 0, 0) if a < 128 else ((8, 8, 8) if not (r or v or b)
                                                 else (r, v, b))
                      for r, v, b, a in carre.getdata()]
            bitmap = (LOGO_PX, LOGO_PX, pixels)
        except Exception:
            bitmap = None
    _LOGO_CACHE[key] = bitmap
    return bitmap


def _draw_logo(frame, flight, logo_dir):
    bitmap = _load_logo(flight.get("airline_icao"), logo_dir)
    if bitmap is not None:
        frame.draw_bitmap(3, 4, bitmap)
        return
    # Repli : silhouette d'avion + code OACI de la compagnie
    frame.draw_char(12, 5, PLANE, SECONDAIRE)
    code = _fit(flight.get("airline_icao") or flight.get("airline_iata") or "", 4)
    if code:
        x = LOGO_X0 + (LOGO_X1 - LOGO_X0 + 1 - font5x7.text_width(code)) // 2
        frame.draw_text(x, 17, code, TEXTE)


def _scroll_offset(text, elapsed):
    span = font5x7.text_width(text) + SCROLL_GAP
    if font5x7.text_width(text) <= TEXT_W:
        return None, span
    return int(elapsed * SCROLL_PX_PER_SEC) % span, span


def render(flight, elapsed=0.0, logo_dir="logos", frame=None, heure=None):
    """Compose une image du panneau.

    flight : dict renvoye par la passerelle, ou None quand le ciel est vide.
    elapsed : secondes ecoulees, pilote le defilement de la ligne du bas.
    frame : cadre existant ou l'on dessine sans effacer, pour superposer deux
    ecrans pendant une transition. Par defaut, un cadre neuf donc noir.
    heure : heure courante, calculee par la passerelle. Le panneau est une
    horloge murale avant tout : elle figure sur chaque ecran de la rotation.
    """
    if frame is None:
        frame = Frame()
    heure = heure or flight_none_clock()

    if not flight:
        frame.draw_text(6, LINE1_Y + 4, "CIEL DEGAGE", SECONDAIRE)
        frame.draw_text(6, LINE3_Y - 3, heure, TEXTE)
        return frame

    frame.vline(SEP_X, 2, HEIGHT - 3, SEP)
    _draw_logo(frame, flight, logo_dir)

    clip = (TEXT_X0, TEXT_X1)

    # Ligne 1 : indicatif du vol, puis niveau de vol aligne a droite
    frame.draw_text(TEXT_X0, LINE1_Y, _fit(flight.get("callsign") or "", 9),
                    PRINCIPAL, clip)
    droite(frame, TEXT_X1, LINE1_Y, flight.get("level") or "", SECONDAIRE, clip)

    # Ligne 2 : origine, fleche, destination, puis l'heure a droite. La
    # ligne 1 est pleine (indicatif et niveau de vol), celle-ci a la place.
    route = "%s %s %s" % (_fit(flight.get("origin") or "???", 3), ARROW,
                          _fit(flight.get("destination") or "???", 3))
    frame.draw_text(TEXT_X0, LINE2_Y, route, ACCENT, clip)
    droite(frame, TEXT_X1, LINE2_Y, heure, SECONDAIRE, clip)

    # Ligne 3 : compagnie et ville de destination, en defilement si trop long
    ticker = flight.get("ticker") or ""
    offset, span = _scroll_offset(ticker, elapsed)
    if offset is None:
        frame.draw_text(TEXT_X0, LINE3_Y, ticker, TEXTE, clip)
    else:
        frame.draw_text(TEXT_X0 - offset, LINE3_Y, ticker, TEXTE, clip)
        frame.draw_text(TEXT_X0 - offset + span, LINE3_Y, ticker, TEXTE, clip)

    return frame


def flight_none_clock():
    return time.strftime("%H:%M")


def build_ticker(flight):
    """Texte defilant : compagnie, ville d'arrivee, appareil, distance.

    L'appareil passe avant la distance : c'est le detail qu'on lit quand on a
    deja identifie le vol, et la distance ferme la phrase.
    """
    parts = []
    if flight.get("airline_name"):
        parts.append(flight["airline_name"])
    if flight.get("destination_city"):
        parts.append(flight["destination_city"])
    if flight.get("aircraft"):
        parts.append(flight["aircraft"])
    if flight.get("distance_km") is not None:
        parts.append("%d KM" % round(flight["distance_km"]))
    if not parts:
        parts.append("ROUTE INCONNUE")
    return ("   " + ARROW + "   ").join(p.upper() for p in parts)
