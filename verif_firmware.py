"""Compile le croquis ESP32 sans le televerser, pour attraper les erreurs tot.

    python3 verif_firmware.py

Le test hors ligne compare les *valeurs* partagees entre Python et C ; il ne
voit pas un point-virgule manquant ni un ordre d'inclusion invalide. Cette
verification-la demande un vrai compilateur.

Elle sort en code 0 si arduino-cli est absent : ce n'est pas une dependance du
projet, seulement un garde-fou pour qui l'a installe. Pour l'installer :

    https://arduino.github.io/arduino-cli/latest/installation/
    arduino-cli config add board_manager.additional_urls \\
        https://espressif.github.io/arduino-esp32/package_esp32_index.json
    arduino-cli core update-index
    arduino-cli core install esp32:esp32
    arduino-cli lib install ArduinoJson
    arduino-cli lib install "ESP32 HUB75 LED MATRIX PANEL DMA Display"

Arduino exige qu'un croquis vive dans un dossier portant son propre nom, or
le notre s'appelle firmware/. On compile donc une copie temporaire plutot que
de renommer le dossier et toutes les references qui le citent.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CROQUIS = "panneau_vols"

# Schema de partition "Minimal SPIFFS" : deux emplacements d'application de
# 1,9 Mo, pour les mises a jour sans fil (OTA). Dans l'IDE Arduino :
# Outils > Partition Scheme > Minimal SPIFFS (1.9MB APP with OTA/190KB SPIFFS).
# ARDUINO_FQBN le remplace, par exemple pour compiler pour l'ESP32-S3.
FQBN = os.environ.get("ARDUINO_FQBN",
                      "esp32:esp32:esp32:PartitionScheme=min_spiffs")

# Avec LOGOS_FACTICES=N, la copie compilee recoit un logos.h de N logos
# factices (des aplats, aucune marque) : c'est le chemin AVEC_LOGOS qui est
# compile, et la taille mesuree est celle du panneau reel. Rien n'est ecrit
# dans firmware/.
LOGOS_FACTICES = int(os.environ.get("LOGOS_FACTICES", "0") or 0)

# En CI, l'absence d'arduino-cli doit echouer, pas etre ignoree.
OBLIGATOIRE = os.environ.get("VERIF_FIRMWARE_OBLIGATOIRE") == "1"


def trouve_cli():
    """arduino-cli sur le PATH, ou designe par la variable ARDUINO_CLI."""
    designe = os.environ.get("ARDUINO_CLI")
    if designe and os.path.exists(designe):
        return designe
    return shutil.which("arduino-cli")


def ecrit_logos_factices(chemin, combien):
    """logos.h de combien logos unis, au format exact d'export_logos."""
    import export_logos
    cote = export_logos.TAILLE
    logos = [("F%02X" % n, [(n * 2654435761) & 0xFFFF] * (cote * cote))
             for n in range(combien)]
    with open(chemin, "w", encoding="ascii") as handle:
        handle.write(export_logos._entete(logos))


def main():
    cli = trouve_cli()
    if not cli:
        print("arduino-cli introuvable : verification ignoree.")
        print("Voir l'en-tete de ce fichier pour l'installer.")
        return 1 if OBLIGATOIRE else 0

    source = os.path.join(HERE, "firmware")
    with tempfile.TemporaryDirectory() as tmp:
        cible = os.path.join(tmp, CROQUIS)
        os.makedirs(cible)
        for nom in sorted(os.listdir(source)):
            if nom.endswith((".ino", ".h")):
                shutil.copy2(os.path.join(source, nom),
                             os.path.join(cible, nom))
        if LOGOS_FACTICES:
            ecrit_logos_factices(os.path.join(cible, "logos.h"),
                                 LOGOS_FACTICES)
        copies = sorted(os.listdir(cible))
        print("croquis : %d fichiers (%s)" % (len(copies), ", ".join(copies)))

        commande = [cli, "compile", "--fqbn", FQBN, "--warnings", "default"]
        # ctags ne sert qu'a generer les prototypes, dont le croquis n'a pas
        # besoin. Sur une machine qui ne peut pas telecharger celui
        # d'arduino.cc, ARDUINO_CTAGS designe un dossier contenant un autre.
        if os.environ.get("ARDUINO_CTAGS"):
            commande += ["--build-property", "runtime.tools.ctags.path=%s"
                         % os.environ["ARDUINO_CTAGS"]]
        resultat = subprocess.run(commande + [cible],
                                  capture_output=True, text=True)

    sortie = (resultat.stdout or "") + (resultat.stderr or "")
    if resultat.returncode == 0:
        # arduino-cli traduit ses messages : on repere les lignes de taille
        # par le pourcentage plutot que par un mot anglais
        for ligne in sortie.splitlines():
            if "%" in ligne and "octet" in ligne.lower():
                print(ligne.strip())
            elif "%" in ligne and ("storage" in ligne or "memory" in ligne):
                print(ligne.strip())
        print("\ncompilation reussie")
        return 0

    print(sortie.strip())
    print("\nCOMPILATION EN ECHEC")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
