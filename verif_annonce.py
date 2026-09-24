"""Compare la regle d'annonce d'avion entre la passerelle et le firmware.

    python3 verif_annonce.py

Le test hors ligne compare des constantes ; ici on compare un comportement.
Un scenario pilote la vraie passerelle Python, et chaque etape donne l'ecran
de fond envoye dans "sc" et le fait qu'une annonce demarre ou non. Le meme
flux est rejoue dans firmware/annonce_vol.h, compile sur le PC : les deux
cotes doivent annoncer aux memes etapes.

S'ignore sans compilateur C++ (g++, clang++ ou c++ sur le PATH, ou designe
par la variable CXX) : ce n'est pas une dependance du projet.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time

import composition
import passerelle

HERE = os.path.dirname(os.path.abspath(__file__))

HARNAIS = r"""
#include <iostream>
#include <string>
#include "annonce_vol.h"

int main() {
  char deja[12] = "";
  std::string ecran, indicatif;
  int ok;
  while (std::cin >> ecran >> indicatif >> ok) {
    if (indicatif == "-") indicatif = "";
    std::cout << (annonceVolDue(ecran.c_str(), ok != 0, indicatif.c_str(),
                                deja, sizeof(deja)) ? 1 : 0) << "\n";
  }
  return 0;
}
"""

VOL_A = {"callsign": "AFR1234", "airline_name": "Air France"}
VOL_B = {"callsign": "EZY83QK", "airline_name": "Easyjet"}
JOUR = [{"nom": n, "adhan": h} for n, h in
        (("FAJR", "05:54"), ("DOHR", "13:45"), ("ASR", "17:09"),
         ("MAGHREB", "19:59"), ("ICHA", "21:22"))]

# (libelle, vol present, ecran de rotation impose ou None, prise de main)
SCENARIO = [
    ("A arrive pendant l'ecran priere", VOL_A, "priere", False),
    ("A attend toujours", VOL_A, None, False),
    ("la rotation passe aux horaires", VOL_A, "horaires", False),
    ("la rotation quitte les prieres", VOL_A, "meteo", False),
    ("A deja annonce", VOL_A, None, False),
    ("B arrive pendant une prise de main", VOL_B, None, True),
    ("la priere rend la main", VOL_B, "heure", False),
    ("le ciel se vide", None, "heure", False),
    ("A revient pendant les horaires", VOL_A, "horaires", False),
    ("A sort des prieres", VOL_A, "adkar", False),
    ("B remplace A a l'ecran", VOL_B, None, False),
]


def compilateur():
    designe = os.environ.get("CXX")
    if designe and shutil.which(designe):
        return shutil.which(designe)
    for nom in ("g++", "clang++", "c++"):
        if shutil.which(nom):
            return shutil.which(nom)
    return None


def cote_python():
    """Rejoue le scenario dans la vraie passerelle : [(sc, indicatif, ok,
    annonce_demarre)]."""
    g = passerelle.Gateway({"rotation_seconds": 30})
    g.current_usage = lambda: None  # pas de releve Claude dans le scenario
    g.meteo = {"temperature": 18, "icone": "nuage", "texte": "COUVERT"}
    etapes = []
    for _, vol, ecran, prise in SCENARIO:
        maintenant = time.time()
        with g.lock:
            g.flight = dict(vol) if vol else None
            g.last_seen = maintenant if vol else 0.0
            g.prieres = {"nom": "ASR", "prise_main": prise, "jour": JOUR,
                         "phase": "adhan" if prise else "attente"}
            g.priere_annoncee = "ASR"  # l'annonce de priere est hors sujet
            if ecran:
                g.rotation_ecran = ecran
                g.rotation_debut = maintenant
        avant = g.alerte
        ecran_obtenu = g.screen()[0]
        sc = composition.ECRAN_DE_FOND.get(ecran_obtenu, ecran_obtenu)
        indicatif = vol["callsign"] if vol else ""
        etapes.append((sc, indicatif, bool(vol), g.alerte != avant))
    return etapes


def cote_c(cxx, etapes):
    """Meme flux dans annonce_vol.h compile : [annonce_demarre]."""
    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "harnais.cpp")
        binaire = os.path.join(tmp, "harnais")
        with open(source, "w", encoding="ascii") as handle:
            handle.write(HARNAIS)
        subprocess.run([cxx, "-std=c++11", "-Wall", "-Werror",
                        "-I", os.path.join(HERE, "firmware"),
                        source, "-o", binaire],
                       check=True, capture_output=True, text=True)
        entree = "".join("%s %s %d\n" % (sc, indicatif or "-", int(ok))
                         for sc, indicatif, ok, _ in etapes)
        sortie = subprocess.run([binaire], input=entree, check=True,
                                capture_output=True, text=True).stdout
    return [ligne.strip() == "1" for ligne in sortie.split()]


def verifie(check):
    """Ajoute les verifications au test hors ligne. Rien sans compilateur."""
    cxx = compilateur()
    if not cxx:
        return False
    etapes = cote_python()
    try:
        c = cote_c(cxx, etapes)
    except subprocess.CalledProcessError as exc:
        check("annonce d'avion : harnais C compile", False,
              (exc.stderr or exc.stdout or "").strip()[:200])
        return True
    check("annonce d'avion : le harnais C rejoue tout le scenario",
          len(c) == len(etapes), "%d etapes sur %d" % (len(c), len(etapes)))
    for (libelle, _, _, _), (sc, _, _, py), en_c in zip(SCENARIO, etapes, c):
        check("annonce d'avion jumelle : %s" % libelle, py == en_c,
              "sc=%s python=%s c=%s" % (sc, "annonce" if py else "-",
                                        "annonce" if en_c else "-"))
    annonces = [libelle for (libelle, _, _, _), (_, _, _, py)
                in zip(SCENARIO, etapes) if py]
    check("annonce d'avion : le scenario annonce quatre fois, hors priere",
          annonces == ["la rotation quitte les prieres",
                       "la priere rend la main", "A sort des prieres",
                       "B remplace A a l'ecran"],
          " / ".join(annonces))
    return True


def main():
    checks = []
    if not verifie(lambda l, c, d="": checks.append((l, bool(c), d))):
        print("compilateur C++ introuvable : verification ignoree.")
        return 0
    for libelle, ok, detail in checks:
        print("%s  %s  %s" % ("OK  " if ok else "ECHEC", libelle, detail))
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
