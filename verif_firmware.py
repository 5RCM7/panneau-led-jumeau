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

# Schema de partition "Huge APP" : avec celui par defaut, le croquis occupe
# 87 % des 1,3 Mo disponibles et il ne reste que 167 Ko, moins que le budget
# de logos. Huge APP porte la partition a 3,1 Mo, soit 36 % d'occupation.
# Dans l'IDE Arduino : Outils > Partition Scheme > Huge APP (3MB No OTA).
FQBN = "esp32:esp32:esp32:PartitionScheme=huge_app"


def trouve_cli():
    """arduino-cli sur le PATH, ou designe par la variable ARDUINO_CLI."""
    designe = os.environ.get("ARDUINO_CLI")
    if designe and os.path.exists(designe):
        return designe
    return shutil.which("arduino-cli")


def main():
    cli = trouve_cli()
    if not cli:
        print("arduino-cli introuvable : verification ignoree.")
        print("Voir l'en-tete de ce fichier pour l'installer.")
        return 0

    source = os.path.join(HERE, "firmware")
    with tempfile.TemporaryDirectory() as tmp:
        cible = os.path.join(tmp, CROQUIS)
        os.makedirs(cible)
        for nom in sorted(os.listdir(source)):
            if nom.endswith((".ino", ".h")):
                shutil.copy2(os.path.join(source, nom),
                             os.path.join(cible, nom))
        copies = sorted(os.listdir(cible))
        print("croquis : %d fichiers (%s)" % (len(copies), ", ".join(copies)))

        resultat = subprocess.run(
            [cli, "compile", "--fqbn", FQBN, "--warnings", "default", cible],
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
