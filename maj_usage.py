"""Ecrit usage.json a partir de ce qu'affiche /usage dans Claude Code.

    python3 maj_usage.py 39 "4h 25m" 48 "5d 7h"
    python3 maj_usage.py 39 2026-09-20T16:20:00 48 2026-09-25T19:00:00

Quatre valeurs : le pourcentage CONSOMME de la fenetre de cinq heures et sa
remise a zero, puis les memes pour la fenetre hebdomadaire. La remise a zero
s'ecrit soit comme la carte /usage l'affiche ("4h 25m", "5d 7h"), soit en
date ISO.

Pourquoi a la main : les chiffres du quota ne sont lisibles que depuis
Claude Code, par sa commande /usage. Il n'y a pas d'API a interroger, donc
pas de sondage possible depuis la passerelle. Le releve est date, et
claudesource.py fait disparaitre l'ecran quand il devient trop vieux plutot
que d'afficher un chiffre perime.
"""

import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLES = ("5H", "7J")

# "5d 7h", "4h 25m", "45m" : ce que la carte /usage affiche telle quelle
DUREE = re.compile(r"(\d+)\s*([dhjm])", re.I)
UNITES = {"d": 1440, "j": 1440, "h": 60, "m": 1}


def echeance(valeur, maintenant):
    """Date de remise a zero, depuis une duree relative ou une date ISO."""
    texte = str(valeur).strip()
    morceaux = DUREE.findall(texte)
    if morceaux and not texte[:1].isdigit() or len(texte) < 11:
        minutes = sum(int(n) * UNITES[u.lower()] for n, u in morceaux)
        if minutes:
            return maintenant + datetime.timedelta(minutes=minutes)
    try:
        quand = datetime.datetime.fromisoformat(texte.replace("Z", "+00:00"))
    except ValueError:
        raise SystemExit("echeance incomprise : %s" % valeur)
    if quand.tzinfo is not None:
        quand = quand.astimezone().replace(tzinfo=None)
    return quand


def pourcent(valeur):
    n = int(str(valeur).strip().rstrip("%"))
    if not 0 <= n <= 100:
        raise SystemExit("pourcentage hors bornes : %s" % valeur)
    return n


def main(argv):
    if len(argv) not in (4, 5):
        print(__doc__.strip().splitlines()[0])
        print("\n  python3 maj_usage.py <5h%> <5h-reset> <7j%> <7j-reset>"
              " [plan]")
        return 1

    maintenant = datetime.datetime.now().replace(microsecond=0)
    fenetres = []
    for n, cle in enumerate(CLES):
        fenetres.append({
            "cle": cle,
            "utilise": pourcent(argv[n * 2]),
            "reset": echeance(argv[n * 2 + 1], maintenant).isoformat(),
        })

    donnees = {"plan": argv[4] if len(argv) == 5 else "Pro",
               "releve": maintenant.isoformat(),
               "fenetres": fenetres}
    chemin = os.path.join(HERE, "usage.json")
    with open(chemin, "w", encoding="utf-8") as handle:
        json.dump(donnees, handle, indent=2, ensure_ascii=True)
        handle.write("\n")

    print("usage.json ecrit :")
    for fenetre in fenetres:
        print("  %-3s %3d %% consommes, remise a zero le %s"
              % (fenetre["cle"], fenetre["utilise"], fenetre["reset"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
