"""Telechargement HTTP a delai total strict, pour toutes les sources.

Le timeout d'urllib borne chaque operation sur la socket, pas la requete
entiere : un serveur qui distille un octet toutes les secondes le respecte
indefiniment. Ici le delai est une echeance : connexion et lecture comprises,
la requete abandonne quand elle est depassee, et la taille est plafonnee.

Toutes les erreurs de transport sortent en urllib.error.URLError, que les
appelants savent deja attraper. Un TimeoutError brut, leve pendant la
lecture, traversait sinon leurs except et faisait echouer tout le sondage
des vols pour une simple route en retard.

Limite connue : la resolution DNS (getaddrinfo) ne se laisse pas
interrompre. Chaque source ayant son propre fil (cf. collecteur.py), un DNS
bloque ne retarde que la sienne.

Uniquement la bibliotheque standard.
"""

import time
import urllib.error
import urllib.request

USER_AGENT = "jumeau-panneau-led/1.0 (projet personnel)"
# Echeance de chaque requete sortante, connexion et lecture comprises. Une
# seule valeur pour toutes les sources : au-dela de cinq secondes, une API
# communautaire est en difficulte, et on sert la derniere valeur connue.
DELAI_MAX = 5.0
TAILLE_MAX = 4 * 1024 * 1024  # la page Mawaqit, la plus lourde, fait ~1 Mo
BLOC = 64 * 1024


class DelaiDepasse(urllib.error.URLError):
    """La requete a depasse son echeance."""


class TropVolumineux(ValueError):
    """La reponse depasse TAILLE_MAX : ce n'est pas ce qu'on attendait."""


def _regle_socket(reponse, secondes):
    """Borne la prochaine lecture au temps qui reste, si on atteint la socket.

    Sans acces a la socket, chaque lecture garde le timeout de connexion :
    l'echeance est alors verifiee entre deux lectures, et le depassement
    borne a une lecture.
    """
    try:
        reponse.fp.raw._sock.settimeout(max(0.05, secondes))
    except AttributeError:
        pass


def lire(url, delai=DELAI_MAX, entetes=None, taille_max=TAILLE_MAX):
    """Octets de la reponse, en delai secondes au plus, connexion comprise.

    Jamais plus que DELAI_MAX, meme si l'appelant demande davantage.
    """
    delai = min(float(delai), DELAI_MAX)
    echeance = time.monotonic() + delai
    requete = urllib.request.Request(
        url, headers=dict(entetes or {}, **{"User-Agent": USER_AGENT}))
    try:
        with urllib.request.urlopen(requete, timeout=delai) as reponse:
            morceaux, total = [], 0
            while True:
                reste = echeance - time.monotonic()
                if reste <= 0:
                    raise DelaiDepasse("delai de %.1f s depasse" % delai)
                _regle_socket(reponse, reste)
                morceau = reponse.read1(BLOC)
                if not morceau:
                    break
                total += len(morceau)
                if total > taille_max:
                    raise TropVolumineux("reponse de plus de %d octets"
                                         % taille_max)
                morceaux.append(morceau)
            return b"".join(morceaux)
    except urllib.error.URLError:
        raise
    except (TimeoutError, OSError) as exc:
        # socket.timeout, connexion coupee... : une seule famille pour les
        # appelants. TropVolumineux n'est pas un OSError et passe tel quel.
        if isinstance(exc, TimeoutError) or time.monotonic() >= echeance:
            raise DelaiDepasse("delai de %.1f s depasse" % delai) from exc
        raise urllib.error.URLError(exc) from exc


def lire_texte(url, delai=DELAI_MAX, entetes=None, taille_max=TAILLE_MAX):
    return lire(url, delai, entetes, taille_max).decode("utf-8", "replace")
