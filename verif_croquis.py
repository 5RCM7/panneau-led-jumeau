"""Verifie dans le source C les regles qui gardent l'affichage vivant.

    python3 verif_croquis.py

Le compilateur accepterait un appel HTTP dans loop() ou un setBrightness8()
depuis la tache reseau : ce sont des erreurs de conception, pas de syntaxe,
et elles ne se voient qu'au mur, par un ecran qui fige ou qui dechire. On les
cherche donc dans le texte, commentaires retires.
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIRMWARE = os.path.join(HERE, "firmware")

# Noms que le croquis attend de secrets.h
SECRETS = ("WIFI_SSID", "WIFI_PASS", "GATEWAY_HOST", "GATEWAY_IP",
           "GATEWAY_PORT")


def lis(nom):
    with open(os.path.join(FIRMWARE, nom), "r", encoding="ascii") as handle:
        return handle.read()


def sans_commentaires(code):
    """Retire les commentaires C, en respectant les chaines."""
    motif = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"', re.S)
    return motif.sub(lambda m: m.group(0) if m.group(0).startswith('"')
                     else "", code)


def corps(code, signature):
    """Corps de la fonction qui suit signature, accolades equilibrees."""
    debut = code.index("{", code.index(signature))
    profondeur = 0
    for n in range(debut, len(code)):
        if code[n] == "{":
            profondeur += 1
        elif code[n] == "}":
            profondeur -= 1
            if profondeur == 0:
                return code[debut:n + 1]
    raise ValueError("fonction incomplete : %s" % signature)


def verifie(check):
    ino = sans_commentaires(lis("panneau_vols.ino"))
    reseau = sans_commentaires(lis("reseau.h"))
    passerelle = sans_commentaires(lis("passerelle.h"))
    boucle = corps(ino, "void loop()")
    demarrage = corps(ino, "void setup()")

    # Le reseau ne touche jamais l'affichage
    for nom, code in (("passerelle.h", passerelle), ("reseau.h", reseau)):
        check("croquis : %s ne touche pas au DMA de l'affichage" % nom,
              not re.search(r"\bdma\b", code))

    # loop() ne fait rien de bloquant
    bloquants = [m for m in ("fetchGateway", "HTTPClient", "WiFi.",
                             "MDNS.", "portMAX_DELAY") if m in boucle]
    check("croquis : rien de bloquant dans loop()", not bloquants,
          ", ".join(bloquants) or "reseau hors de la boucle d'affichage")
    check("croquis : setup() n'attend pas le Wi-Fi",
          "WiFi.status" not in demarrage and "while" not in demarrage)
    prise = corps(reseau, "static bool recupereEtat(")
    check("croquis : le Core 1 tente le verrou sans attendre",
          re.search(r"xSemaphoreTake\(\s*g_verrou\s*,\s*0\s*\)", prise))
    check("croquis : loop() recopie l'etat par recupereEtat",
          "recupereEtat(" in boucle)
    tache = re.search(r"xTaskCreatePinnedToCore\(([^;]*)\);", reseau)
    check("croquis : la tache reseau est epinglee sur le Core 0",
          tache and tache.group(1).split(",")[-1].strip() == "0",
          " ".join(tache.group(0).split()) if tache else "introuvable")
    check("croquis : fetchGateway n'est appele que par la tache reseau",
          "fetchGateway(" in corps(reseau, "static void tacheReseau(")
          and "fetchGateway(" not in ino)

    # Double tampon, et un temps d'image complet apres chaque echange
    check("croquis : double tampon active",
          re.search(r"cfg\.double_buff\s*=\s*true", demarrage))
    dernier_dessin = boucle.rfind("dessineEcran(")
    echange = boucle.rfind("flipDMABuffer()")
    check("croquis : l'image s'echange apres le dernier dessin",
          echange > dernier_dessin >= 0)
    marge = re.search(r"APRES_FLIP_MS\s*=\s*(\d+)", ino)
    check("croquis : au moins une image a 60 Hz entre echange et ecriture",
          marge and int(marge.group(1)) * 60 >= 1000,
          "%s ms" % (marge.group(1) if marge else "?"))

    # Les secrets restent hors du depot
    with open(os.path.join(HERE, ".gitignore"), encoding="utf-8") as handle:
        ignores = handle.read().split()
    check("croquis : firmware/secrets.h est ignore par git",
          "firmware/secrets.h" in ignores)
    try:
        suivis = subprocess.run(["git", "ls-files", "firmware/secrets.h"],
                                cwd=HERE, capture_output=True,
                                text=True).stdout.strip()
    except OSError:
        suivis = ""
    check("croquis : secrets.h n'est pas versionne", not suivis, suivis)
    modele = lis("secrets.exemple.h")
    manquants = [n for n in SECRETS if not re.search(r"\b%s\b\s*=" % n,
                                                     modele)]
    check("croquis : le modele de secrets porte les cinq reglages",
          not manquants, ", ".join(manquants))
    en_dur = [n for n in SECRETS if re.search(r"\b%s\b\s*=" % n, ino)]
    ip = re.findall(r'"\d{1,3}(?:\.\d{1,3}){3}', ino + reseau + passerelle)
    check("croquis : ni mot de passe ni adresse en dur dans le croquis",
          not en_dur and not ip, ", ".join(en_dur + ip))


def main():
    checks = []
    verifie(lambda l, c, d="": checks.append((l, bool(c), d)))
    for libelle, ok, detail in checks:
        print("%s  %s  %s" % ("OK  " if ok else "ECHEC", libelle, detail))
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
