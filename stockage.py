"""Lecture et ecriture des caches JSON sur disque, sans jamais les corrompre.

Ecrire directement dans le fichier le laissait a moitie ecrit si le PC
s'arretait au mauvais moment : au redemarrage, le cache illisible etait
jete, et avec lui le calendrier de priere qui permet de tenir des semaines
sans reseau. On ecrit donc a cote, puis os.replace() substitue le fichier
d'un seul geste : le lecteur voit l'ancien ou le nouveau, jamais un melange.
"""

import json
import os
import tempfile


def lit_json(chemin):
    """Contenu du fichier, ou {} s'il manque ou ne se lit pas."""
    try:
        with open(chemin, "r", encoding="utf-8") as handle:
            donnees = json.load(handle)
    except (OSError, ValueError):
        return {}
    return donnees if isinstance(donnees, dict) else {}


def ecrit_json_atomique(chemin, donnees):
    """Ecrit donnees dans chemin d'un seul geste. Vrai si c'est fait.

    Une erreur d'ecriture n'est pas fatale : le cache reste en memoire, et
    le prochain enregistrement reessaiera.
    """
    dossier = os.path.dirname(os.path.abspath(chemin))
    try:
        descripteur, provisoire = tempfile.mkstemp(
            prefix="." + os.path.basename(chemin) + ".", suffix=".tmp",
            dir=dossier)
    except OSError:
        return False
    try:
        with os.fdopen(descripteur, "w", encoding="utf-8") as handle:
            json.dump(donnees, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(provisoire, chemin)
        return True
    except (OSError, TypeError, ValueError):
        try:
            os.remove(provisoire)
        except OSError:
            pass
        return False
