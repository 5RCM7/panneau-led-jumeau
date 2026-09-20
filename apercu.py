"""Rend une capture du panneau sans lancer le serveur : python3 apercu.py

Utile pour verifier la mise en page et la lisibilite de la police.
"""

import sys

import panel

DEMO = {
    "callsign": "AFR1234",
    "airline_name": "Air France",
    "airline_icao": "AFR",
    "origin": "CDG",
    "destination": "JFK",
    "destination_city": "New York",
    "level": "FL340",
    "distance_km": 4.2,
}


def main():
    elapsed = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    flight = dict(DEMO)
    flight["ticker"] = panel.build_ticker(flight)
    frame = panel.render(flight, elapsed)
    with open("apercu.png", "wb") as handle:
        handle.write(frame.to_png_bytes(scale=6))
    print("apercu.png ecrit (%dx%d)" % (panel.WIDTH * 6, panel.HEIGHT * 6))


if __name__ == "__main__":
    main()
