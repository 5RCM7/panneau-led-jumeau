"""Un fil par source de donnees : aucune API ne peut retarder les autres.

Prieres, meteo et vols etaient sondes l'un apres l'autre dans une seule
boucle : Mawaqit en retard, et les vols attendaient avec lui. Pire, une
exception imprevue dans cette boucle tuait le fil, et la passerelle servait
ensuite indefiniment un etat fige. Chaque source a maintenant son fil, qui :

  - ne meurt jamais : toute exception devient une erreur rapportee ;
  - garde la derniere valeur connue : l'etape n'ecrase l'etat qu'en cas de
    succes, c'est a elle d'y veiller ;
  - espace ses essais quand la source echoue (periode doublee a chaque
    echec, plafonnee) : les APIs sont communautaires, on ne les martele pas
    pendant qu'elles sont en panne.

Les delais stricts sont ceux de telechargement.lire, cote reseau.
"""

import threading
import time

PERIODE_MAX = 600.0  # dix minutes entre deux essais, au plus


class Collecteur:
    """Execute etape() toutes les periode secondes dans son propre fil.

    etape() renvoie None si tout va bien, ou l'erreur (texte ou exception)
    si la source n'a pas repondu. rapporte(nom, erreur, duree) est appele
    apres chaque tour, qu'il reussisse ou non.
    """

    def __init__(self, nom, etape, periode, rapporte, periode_max=PERIODE_MAX):
        self.nom = nom
        self.etape = etape
        self.periode = float(periode)
        self.periode_max = max(self.periode, float(periode_max))
        self.rapporte = rapporte
        self.echecs = 0
        self.fil = None

    def tour(self):
        """Un essai. Renvoie l'attente avant le suivant, en secondes."""
        debut = time.monotonic()
        try:
            erreur = self.etape()
        except Exception as exc:  # le fil de collecte ne doit jamais mourir
            erreur = exc
        duree = time.monotonic() - debut
        self.echecs = self.echecs + 1 if erreur else 0
        try:
            self.rapporte(self.nom, erreur, duree)
        except Exception:
            pass
        return max(0.0, self.periode_courante() - duree)

    def periode_courante(self):
        """Periode normale, doublee a chaque echec d'affilee, plafonnee."""
        if not self.echecs:
            return self.periode
        return min(self.periode * (2 ** min(self.echecs, 10)),
                   self.periode_max)

    def boucle(self, arret):
        while not arret.is_set():
            arret.wait(self.tour())

    def demarre(self, arret):
        self.fil = threading.Thread(target=self.boucle, args=(arret,),
                                    name="collecte-" + self.nom, daemon=True)
        self.fil.start()
        return self.fil
