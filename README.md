# Jumeau numérique — panneau LED « gare » des vols au-dessus de la maison

Un panneau LED 128×32 façon affichage de gare, qui montre en direct le vol qui
passe au-dessus de chez vous : indicatif, compagnie, origine → destination.

Le projet est un **jumeau numérique** : le simulateur PC et le vrai panneau
consomment le même JSON et partagent la même police et la même mise en page.
On met tout au point à l'écran, puis on branche le matériel.

```
     APIs publiques                passerelle              affichage
  ┌──────────────────┐       ┌──────────────────┐     ┌──────────────────┐
  │ adsb.lol   (pos) │──────▶│                  │────▶│ simulateur web   │
  │ adsbdb.com (route)│      │  server.py       │     │ (panel.py)       │
  │ hexdb.io   (repli)│      │  /flight  /frame │     ├──────────────────┤
  └──────────────────┘       └──────────────────┘────▶│ ESP32 + HUB75    │
                                                       │ (panneau_vols)   │
                                                       └──────────────────┘
```

## Démarrage rapide

```bash
python3 server.py
```

Puis ouvrez <http://localhost:8080>. Aucune dépendance à installer : tout tient
dans la bibliothèque standard (Pillow est optionnel, uniquement pour les logos).

Avant le premier lancement, mettez vos coordonnées dans `config.json` :

| Clé | Rôle |
| --- | --- |
| `latitude`, `longitude` | position de la maison (l'exemple pointe le centre de Paris) |
| `search_radius_nm` | rayon interrogé auprès d'adsb.lol, en milles nautiques |
| `max_distance_km` | au-delà, l'avion n'est plus « au-dessus » |
| `bascule_km` | hystérésis : l'avion affiché garde l'écran tant qu'aucun autre n'est plus proche de cette marge (1 km par défaut) |
| `min_altitude_ft` | filtre les avions au sol et en approche basse |
| `poll_seconds` | cadence d'interrogation (12 s est raisonnable) |
| `hold_seconds` | durée d'affichage du dernier vol connu |
| `demo_mode` | `true` pour faire défiler trois vols fictifs, sans réseau |
| `mosquee_slug` | fin de l'URL Mawaqit de la mosquée, ou `null` pour désactiver |
| `priere_avant_min` | minutes avant l'adhan où la prière passe devant l'avion |
| `priere_apres_min` | minutes après l'iqama où elle rend la main |
| `rotation_seconds` | durée par défaut d'une scène, si `duree_ecrans` ne la cite pas |
| `duree_ecrans` | durée par écran, en secondes |
| `meteo_lieu` | nom du lieu affiché sur l'écran météo |
| `luminosite_jour`, `luminosite_nuit` | intensité du panneau, 0-255 |
| `nuit_debut`, `nuit_fin` | plage de veille nocturne, en heures |

`config.json` n'est pas versionné, puisqu'il contient la position du domicile.
Partez de `config.exemple.json`, qui porte les mêmes clés avec des coordonnées
neutres.

Passez `demo_mode` à `true` pour travailler la mise en page sans dépendre du
trafic réel — pratique le soir ou si aucun avion ne passe. Il alimente les
**six écrans** de la rotation, sans aucun appel réseau. Le septième,
Claude Code, dépend d'un relevé `/usage` et disparaît sans lui.

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `font5x7.py` | police bitmap 5×7, source unique de vérité |
| `panel.py` | écran des vols : logo, indicatif, route, bandeau |
| `ecran_prieres.py` | deuxième mise en page : écran des horaires de prière |
| `ecran_horaires.py` | tableau des cinq horaires de prière du jour |
| `ecran_alerte.py` | annonces : avion qui traverse, mosquée qui se pose |
| `transitions.py` | roulement vertical d'un écran à l'autre |
| `ecran_meteo.py` | écran météo et son annonce |
| `ecran_heure.py` | écran de l'heure, et format de la date |
| `ecran_adkar.py` | écran adkar : le nom d'Allah du jour |
| `ecran_claude.py` | écran Claude Code : étoile animée et quota |
| `ecran_annonces.py` | bandeau des annonces de la mosquée |
| `annonces.py` | annonces lues dans le confData, filtrées et nettoyées |
| `ecran_liaison.py` | écran de liaison perdue |
| `audio.py` | quel son jouer, à quel volume |
| `claudesource.py` | lecture d'`usage.json`, calcul de ce qui reste |
| `maj_usage.py` | écrit `usage.json` depuis les chiffres de `/usage` |
| `icones_meteo.py` | les sept silhouettes météo |
| `meteosource.py` | appel et cache d'Open-Meteo |
| `cadre.py` | tampon de pixels et primitives de dessin |
| `passerelle.py` | sondage des sources, rotation, annonces |
| `composition.py` | charge utile ESP32 et composition de l'image |
| `flightsource.py` | appels aux APIs, choix de l'avion, cache des routes |
| `prieresource.py` | récupération et cache du calendrier Mawaqit |
| `horaires.py` | lecture du calendrier : quelle prière afficher, et quand |
| `server.py` | passerelle HTTP + page de simulation |
| `apercu.py` | rend une image PNG sans lancer le serveur |
| `apercu_html.py` | génère `apercu.html`, aperçu navigable des scènes |
| `export_font.py` | régénère `firmware/font5x7.h` depuis `font5x7.py` |
| `export_logos.py` | convertit `logos/*.png` en `firmware/logos.h` (RGB565) |
| `export_arabe.py` | génère les noms de prières en arabe |
| `arabe.py` | silhouettes arabes (généré) |
| `adkar_source.py` | **contenu** des 99 noms : c'est ici qu'on corrige |
| `export_adkar.py` | génère les 99 noms d'Allah |
| `adkar.py` | silhouettes des 99 noms (généré) |
| `verif_firmware.py` | compile le croquis ESP32 sans le téléverser |
| `firmware/panneau_vols.ino` | croquis Arduino pour l'ESP32 |
| `firmware/ecran_prieres.h` | écran des prières côté firmware |
| `firmware/ecran_horaires.h` | tableau des horaires côté firmware |
| `firmware/ecran_alerte.h` | annonces côté firmware |
| `firmware/transitions.h` | transitions côté firmware |
| `firmware/ecran_meteo.h` | écran météo côté firmware |
| `firmware/ecran_heure.h` | écran de l'heure côté firmware |
| `firmware/ecran_adkar.h` | écran adkar côté firmware |
| `firmware/ecran_claude.h` | écran Claude Code côté firmware |
| `firmware/ecran_annonces.h` | bandeau des annonces côté firmware |
| `firmware/ecran_liaison.h` | écran de liaison perdue côté firmware |
| `firmware/audio.h` | pilote DFPlayer Mini |
| `firmware/icones_meteo.h` | silhouettes météo côté firmware |
| `firmware/arabe.h` | silhouettes arabes (généré) |
| `firmware/adkar.h` | silhouettes des 99 noms (généré) |
| `firmware/ecran_vol.h` | écran des vols côté firmware |
| `firmware/passerelle.h` | client HTTP côté firmware |
| `firmware/font5x7.h` | police exportée en C (généré, ne pas éditer) |
| `firmware/logos.h` | logos en RGB565 (généré, non versionné) |

## Endpoints

| URL | Contenu |
| --- | --- |
| `/` | simulateur : rendu LED animé + état de la passerelle |
| `/flight` | JSON compact consommé par l'ESP32 : vol, prière et écran à afficher |
| `/flight/full` | JSON complet du vol, pour mise au point |
| `/prieres` | JSON complet de la prière courante, pour mise au point |
| `/meteo` | JSON complet de la météo courante, pour mise au point |
| `/frame` | tampon de pixels courant en base64, utilisé par le simulateur |
| `/snapshot.png` | capture PNG du panneau à l'instant t |

Le bandeau défilant enchaîne **compagnie → ville d'arrivée → appareil →
distance**. L'appareil passe avant la distance : c'est le détail qu'on lit une
fois le vol identifié, et la distance ferme la phrase.

```
AIR FRANCE  →  NEW YORK  →  BOEING 777 328ER  →  4 KM
```

Les noms venus des APIs sont **réduits à l'ASCII à la source** : la police ne
connaît pas les accents et rendrait « São Paulo » en « S?O PAULO ». Le
nettoyage a lieu dans `build_flight()`, donc l'ESP32 reçoit déjà des champs
propres — il n'a pas de quoi le faire lui-même.

Exemple de charge utile `/flight` :

```json
{"ok":true,"cs":"AFR1234","al":"Air France","ic":"AFR",
 "fr":"CDG","to":"JFK","ct":"New York","lv":"FL340","km":4.2,
 "sc":"vol",
 "pr":{"n":"MAGHREB","a":"19:59","i":"20:04","r":"52 MIN",
       "m":"MOSQUEE","h":"19:07","u":false,"e":false,"d":false}}
```

`sc` porte l'écran à afficher. La rotation et les priorités sont décidées
dans la passerelle, une seule fois : le firmware obéit, ce qui évite que les
deux moitiés du jumeau divergent. `sc` porte toujours l'écran de fond, jamais
le nom d'une annonce, que le firmware ne saurait pas lire.

## Horaires de prière

Le panneau affiche la prochaine prière de la mosquée configurée. Deux règles :

- **ciel vide** → les horaires remplacent l'écran de veille ;
- **autour de l'horaire** → la prière passe devant l'avion, de
  `priere_avant_min` avant l'adhan jusqu'à `priere_apres_min` après l'iqama.

Entre l'adhan et l'iqama, le panneau reste sur la prière en cours et décompte
vers l'iqama : c'est le temps qu'il reste pour rejoindre la mosquée.

```
MOSQUEE                    19:08
---------------------------------
MAGHREB                    19:59
IQAMA 20:04               51 MIN
```

Le vendredi, la prière de midi devient la Joumoua à l'heure annoncée par la
mosquée — souvent avant le dohr astronomique, d'où l'heure unique et la ligne
du bas vide.

## Rotation des écrans

Le panneau change de scène toutes les `rotation_seconds` (30 s par défaut) :

```
vol → prière → horaires → annonces → météo → adkar → Claude Code → heure
```

Les écrans indisponibles sont sautés : pas d'avion dans le rayon, pas d'écran
de vol. Deux choses passent devant la rotation — une prière qui prend la main,
et un avion qui vient d'arriver, lequel garde ensuite l'écran un tour complet.

Le bandeau des horaires fait défiler la journée entière, chaque prière
annoncée **en arabe puis en français**, à la manière d'un bandeau de chaîne
d'info. La prochaine prière est en surbrillance.

```
MOSQUEE                             23:07
[arabe] FAJR 05:55   [arabe] DOHR 13:45  ...
```

L'arabe ne peut pas sortir de la police 5×7, qui est ASCII pure : il demande
des formes contextuelles et une écriture de droite à gauche. Les six noms
sont donc des **silhouettes**, rendues une fois pour toutes depuis une vraie
police par `export_arabe.py`. Le panneau n'a besoin d'aucune bibliothèque
supplémentaire, il lit les fichiers générés.

Un tour complet dure une quarantaine de secondes à 22 px/s, d'où les 45 s
d'affichage : assez lent pour se lire de loin, assez rapide pour ne pas
paraître figé.

La passerelle ne transmet que les heures, en une seule chaîne — les noms
étant fixes des deux côtés, les envoyer aurait doublé le champ pour rien.

### Tempo et priorités

Chaque scène a sa propre durée, réglable par `duree_ecrans` :

| Écran | Durée | Pourquoi |
| --- | --- | --- |
| Horaires | 45 s | le bandeau met 39 s à faire un tour |
| Annonces | 30 s et plus | au moins un tour complet du bandeau |
| Prochaine prière | 40 s | l'information la plus utile |
| Adkar | 30 à 36 s | au moins un tour complet de la signification |
| Claude Code | 15 s | deux jauges, ça se lit d'un coup d'œil |
| Vol | 25 s | son bandeau boucle en 16 s |
| Météo | 25 s | se lit d'un coup d'œil |
| Heure | 20 s | l'heure figure déjà partout ailleurs |

Cycle complet : **3 min 50 à 4 min**, selon la longueur de la
signification du jour et le nombre d'annonces. Une durée unique conviendrait
mal, le bandeau et l'horloge n'ayant pas les mêmes besoins.

## Annonces de la mosquée

Ce que la mosquée publie sur Mawaqit passe en bandeau défilant, dans le même
langage visuel que les horaires.

```
MOSQUEE                             23:07
CONFERENCE VENDREDI 20H  *  COURS D'ARABE
```

Rien de plus à télécharger : les annonces voyagent dans le même `confData`
que les horaires, déjà en cache. Une limite du format côté Mawaqit : le corps
de l'annonce est presque toujours une **image**, que 128 pixels de large ne
sauraient rendre. Seul le titre est exploitable — ce qui suffit à dire qu'il
se passe quelque chose, et quand.

Les titres viennent d'un site tiers : ils sont ramenés à ce que la police 5×7
sait écrire, tronqués à 44 caractères, et limités à trois. Les annonces hors
de leur fenêtre de diffusion sont écartées. Pas d'annonce publiée, pas
d'écran — la mosquée décide.

## Adhan et iqama

Un **DFPlayer Mini** (~4 €) joue l'adhan aux cinq prières, et un signal court
à l'iqama. Le son sort du panneau lui-même, pas d'un PC ailleurs dans la
maison.

### Pourquoi ce module et pas un ampli I2S

La bibliothèque du panneau s'appelle `ESP32-HUB75-MatrixPanel-I2S-DMA` : elle
tient le périphérique I2S et la DMA en permanence pour rafraîchir les LED.
Décoder un MP3 sur le même ESP32 reviendrait à disputer la DMA à l'affichage,
et à faire scintiller le panneau pendant les trois minutes de l'adhan. Le
DFPlayer décode et amplifie dans son coin : deux broches, et l'affichage ne
s'aperçoit de rien.

### Câblage

| DFPlayer | ESP32 |
| --- | --- |
| VCC | 5 V (la même alimentation que le panneau) |
| GND | GND |
| RX | GPIO 18, **au travers d'une résistance de 1 kΩ** |
| TX | GPIO 35 (entrée seule, ce qui suffit) |
| SPK_1 / SPK_2 | petit haut-parleur 3 W |
| DAC_R / GND | ou entrée ligne d'une enceinte amplifiée, bien meilleur |

Il reste les GPIO 21, 22 et 33 libres après ça, de quoi ajouter un bouton
plus tard.

### Carte microSD, formatée en FAT32

```
/mp3/0001.mp3   l'adhan
/mp3/0002.mp3   le signal court de l'iqama
```

Les fichiers sont à vous : la récitation est un choix personnel, le dépôt
n'en embarque aucune.

### Quand ça sonne

| Moment | Ce qui se passe | Son |
| --- | --- | --- |
| l'heure de la prière — 19:59 | l'adhan | `0001.mp3` |
| l'heure de l'iqama — 20:04 | la prière commence | `0002.mp3` |

Un test parcourt la journée minute par minute et compare ce qui sonne aux
horaires de la mosquée : dix déclenchements par jour, aux dix heures
annoncées, et rien entre.

> **Piège pour qui touchera à `audio.py`.** Le nom des phases dans
> `horaires.py` désigne ce qu'on **attend**, pas ce qui vient d'arriver : on
> est en phase `adhan` tant que l'adhan n'a pas sonné, et en phase `iqama`
> une fois qu'il a sonné. Entrer dans une phase, c'est donc franchir l'heure
> de la précédente — d'où la table `SON_A_L_ENTREE`, qui paraît décalée d'un
> cran quand on la lit trop vite.

**La ponctualité tient à un détail.** La prière courante est recalculée à
chaque demande, et non gardée depuis le dernier sondage : le réseau n'est
sollicité qu'une fois par jour pour le `confData`, mais le calcul du
franchissement d'heure est pur et instantané (0,03 ms). Servir un instantané
vieux d'un tour de boucle ferait retentir l'adhan jusqu'à douze secondes
après la mosquée.

C'est `audio.py` qui décide, côté passerelle, et qui envoie une **clé**
(`MAGHREB:iqama`). Le firmware joue quand la clé change — sans quoi l'adhan
repartirait à chaque interrogation, toutes les trois secondes. À la première
réponse après un démarrage, la clé est notée sans être jouée : un
redémarrage pendant la fenêtre d'une prière ne relance pas l'adhan dans le
salon.

Le volume suit **la même nuit que la luminosité** (`nuit_debut` /
`nuit_fin`) : `volume_jour` 22, `volume_nuit` 12, sur l'échelle 0–30 du
DFPlayer. `"audio_actif": false` coupe tout.

## Liaison perdue

Le panneau n'a ni horloge sauvegardée ni client NTP : l'heure lui vient de la
passerelle, comme le reste. Passerelle muette, heure figée — et une horloge
murale qui affiche avec aplomb l'heure d'il y a vingt minutes est pire qu'un
écran noir, parce qu'on la croit.

```
        LIAISON PERDUE
       HEURE NON FIABLE
         DEPUIS 4 MIN
```

Après 90 s sans réponse (trente interrogations manquées), le firmware impose
cet écran **contre le champ `sc`**. C'est la seule exception à la règle « la
passerelle mène la rotation », et pour une raison simple : elle ne peut pas
signaler son propre silence.

## Claude Code

L'étoile à onze branches tourne, et deux jauges montrent ce qu'il **reste**
de quota — pas ce qui est consommé, parce que c'est ce qu'on regarde en
passant devant.

```
CLAUDE CODE                         23:07
 ✳   5H [######----]  61%  4H25
 ✳   7J [#####-----]  52%  5J6H
```

Onze branches, donc un onzième de tour ramène la figure sur elle-même : huit
phases suffisent à boucler sans raccord. La jauge passe du vert à l'orange
sous 20 % restants.

**Les chiffres se relèvent à la main.** Il n'y a pas d'API à interroger : le
quota n'est lisible que depuis Claude Code, par sa commande `/usage`. On
reporte ce qu'elle affiche :

```bash
python3 maj_usage.py 39 "4h 25m" 48 "5d 7h"
```

Les deux pourcentages sont ceux **consommés**, tels que la carte les donne ;
l'écran affiche le complément. Le relevé est daté, et tout ce qui dépend de
l'horloge — les comptes à rebours, la péremption — se recalcule à chaque
lecture.

Un relevé de plus de `usage_age_max_heures` (24 par défaut) fait disparaître
l'écran de la rotation, plutôt que d'afficher un chiffre périmé. De même,
une fenêtre dont l'heure de remise à zéro est passée s'affiche `--` et non
`0%` : la consommation a repris depuis, on ne sait plus où elle en est.

`usage.json` n'est pas versionné, comme `config.json`. Partez de
`usage.exemple.json`.

## Le nom d'Allah du jour

Un des **99 noms** par jour, d'après at-Tirmidhi : le nom en arabe au centre,
et en dessous sa translittération, son sens court et sa signification, qui
défilent.

```
ADKAR 8/99                          23:07
            [arabe]
AL-AZIZ - LE TOUT PUISSANT - PUISSANT ET IN…
```

Un par jour, et non un qui tourne à la minute : on a le temps de le retenir,
et le panneau ne ressemble pas à un bandeau publicitaire. Les 99 font un
cycle de trois mois. Le rang se déduit de la date seule — aucun état à
garder, et le même nom toute la journée même si le serveur redémarre.

L'écran reste à l'antenne **au moins le temps d'un tour complet** de sa ligne
défilante : celle-ci met de 22 à 34 s selon le nom, donc la durée s'allonge
quand il le faut. Une phrase coupée en deux ne servirait à personne, et un
test le vérifie pour les 99 jours.

Comme les noms de prières, l'arabe est fait de **silhouettes** générées par
`export_adkar.py`. Le contenu se corrige dans `adkar_source.py`, jamais dans
les fichiers générés. La passerelle transmet le rang dans le champ `ad`,
comme elle transmet l'écran : les deux moitiés du jumeau montrent ainsi
toujours le même nom.

L'ordre de priorité, du plus fort au plus faible :

1. **Adhan et iqama** — la prière prend la main et garde l'écran de
   `priere_avant_min` avant l'appel jusqu'à `priere_apres_min` après l'iqama ;
2. **Écrans de prière** — un avion qui arrive ne les interrompt pas. Son
   annonce n'est pas perdue, elle attend que la rotation passe à autre chose ;
3. **Arrivée d'un avion** — s'annonce et garde l'écran un tour complet ;
4. **La rotation**, pour tout le reste.

C'est la passerelle qui mène la rotation ; le firmware obéit au champ `sc`.
Il interroge donc la passerelle toutes les 3 s et non plus 12 : c'est une
requête sur le réseau local, elle ne coûte rien, et c'est la passerelle qui
ménage les APIs publiques à son propre rythme.

## Veille nocturne

Le panneau baisse d'intensité la nuit : un 128×32 à pleine puissance dans un
salon à trois heures du matin est insupportable.

| Clé | Rôle |
| --- | --- |
| `luminosite_jour` | 0-255, 40 suffit en journée |
| `luminosite_nuit` | 0-255, **0 éteint** le panneau au lieu de le tamiser |
| `nuit_debut`, `nuit_fin` | bornes de la plage ; peut traverser minuit |

Chaque borne accepte trois formes : une heure pleine (`23`), une heure précise
(`"23:30"`), ou le mot **`"fajr"`** — la nuit finit alors quand la mosquée
appelle, et suit les saisons toute seule.

```json
"nuit_debut": 23,
"nuit_fin": "fajr"
```

Mettre `nuit_debut` égal à `nuit_fin` désactive la veille plutôt que d'allumer
une nuit permanente. Si les horaires de prière sont indisponibles, `"fajr"`
retombe sur 7 h plutôt que de laisser le panneau tamisé toute la journée.

C'est la passerelle qui décide, et transmet le niveau dans le champ `br` ; le
firmware appelle `setBrightness8()`.

Le simulateur montre la baisse **relative**, pas le niveau brut. `40` sur 255
donne un panneau LED confortable parce qu'à fond il éblouit ; appliquer ce
même 40 aux pixels d'un moniteur donnerait une image à 16 %, illisible en
plein jour. Le simulateur reste donc à pleine intensité la journée et adopte
le rapport nuit/jour du vrai panneau la nuit venue. L'aperçu `apercu.html`,
lui, ne s'atténue jamais : c'est un outil de mise en page.

## Heure

Le panneau est une **horloge murale avant tout** : l'heure figure sur les cinq
scènes de la rotation et sur l'écran de veille, jamais sur une annonce ni
pendant une transition.

| Écran | Où |
| --- | --- |
| Vol | ligne du milieu, à droite de la route |
| Prochaine prière | en-tête, à droite |
| Horaires du jour | case libre en bas à droite |
| Météo | ligne du milieu, à droite |
| Veille | sous « CIEL DEGAGE » |

Sur l'écran vol, la ligne du haut est pleine — indicatif et niveau de vol n'y
laissent que 23 pixels alors qu'il en faut 29 — d'où le placement sur la ligne
du milieu, qui en a 11 de marge après la route.

Sur le tableau des horaires, l'heure a pris la place du nom de la mosquée :
les deux ne tenaient pas dans les 57 pixels de la case, et le nom reste
visible sur l'écran des prières.

Une scène entière ne montre que l'heure, à l'échelle 3, la date en dessous :

```
        23:07
    SAMEDI 19 SEPT
```

Le texte agrandi n'interpole pas : chaque pixel de la police devient un carré.
Sur un panneau LED, un gros chiffre net vaut mieux qu'un gros chiffre flou.

L'heure apparaît aussi à droite de la ligne du milieu sur l'écran météo.

Elle vient de la passerelle dans les deux cas, jamais de l'ESP32 : celui-ci n'a
ni horloge sauvegardée ni client NTP, choix délibéré depuis l'écran des
prières. Cet écran est donc toujours disponible dans la rotation, puisqu'il ne
dépend d'aucune source réseau.

## Météo

Le temps qu'il fait au-dessus de la maison, via **Open-Meteo** — gratuit, sans
clé, comme les autres sources :

```
[icône]  18°C        ~16°C
COUVERT             23:07
PARIS           12 KM/H
```

Sept silhouettes couvrent les codes WMO : clair de jour, clair de nuit,
éclaircies, couvert, pluie, neige, orage. Le brouillard emprunte le nuage et
la bruine la pluie — sur dix-sept pixels de large, la nuance ne passerait pas.

L'icône voyage vers l'ESP32 sous forme de **rang**, pas de nom : les sept
silhouettes sont fixes des deux côtés, un entier suffit à les désigner.

Open-Meteo rafraîchit au quart d'heure, le cache suit la même cadence. Si le
réseau tombe, la dernière valeur connue reste affichée : une température d'il
y a une heure est plus juste qu'un écran vide.

Le degré `°` a demandé un glyphe de plus dans `font5x7.py`, régénéré dans le
firmware par `export_font.py`.

## Annonces

Ce qui arrive est annoncé avant d'être détaillé. Les deux annonces durent
2,2 s, puis le roulement habituel amène l'écran complet.

**Nouvel indicatif** — une silhouette d'avion traverse la bande du haut de
droite à gauche, à vitesse constante :

```
        ~~~~>
   AVION AU DESSUS
      AFR1234
```

**Prière qui prend la main** — une mosquée entre par la droite et se pose au
centre, en freinant :

```
        [^]
   C'EST L'HEURE
      MAGHREB
```

**Tour de la météo** — l'icône du jour entre et se pose de la même façon :

```
      [icône]
   METEO PARIS
    18°C  COUVERT
```

Celle-ci se déclenche à l'arrivée du tour et non sur un changement de donnée :
le temps qu'il fait n'arrive pas, il est déjà là. Elle est plafonnée à la
moitié d'un tour, sans quoi un `rotation_seconds` court la ferait manger
l'écran météo tout entier.

L'avion traverse, la mosquée se pose : un avion passe au-dessus, une mosquée
non. C'est la même courbe d'adoucissement que les transitions qui donne le
freinage.

Contrairement à l'arbitrage vol/prière, qui est décidé par la passerelle,
**les annonces sont déclenchées de chaque côté** avec la même règle et la même
durée. C'est nécessaire : l'ESP32 n'interroge la passerelle que toutes les
douze secondes et manquerait une fenêtre de deux secondes.

## Transitions

Le passage d'un écran à l'autre n'est pas brutal : l'écran sortant monte,
l'entrant le suit par le bas, en 450 ms. C'est le mouvement d'une pancarte qui
tourne dans un tableau de gare.

Aucun tampon supplémentaire n'est nécessaire. Les deux écrans sont dessinés
dans la même image, décalés verticalement, et ce qui déborde est perdu — un
`dy` dans `Frame.set()` côté Python, dans `px()` côté C. C'est pour cela que
les fonctions de rendu **n'effacent plus l'écran elles-mêmes** : l'appelant le
fait une fois, puis superpose.

La courbe est un `t²(3−2t)`, identique des deux côtés : en linéaire, l'à-coup
de début et de fin se voit nettement sur 32 pixels de haut.

Pour voir les quatorze scènes sans attendre le bon moment de la journée :

```bash
python3 apercu_html.py
```

## Sources de données

Toutes gratuites, sans clé ni inscription :

- **[adsb.lol](https://api.adsb.lol/docs)** — positions ADS-B en temps réel,
  interrogées par rayon autour d'un point.
- **[adsbdb.com](https://www.adsbdb.com/)** — deux usages : indicatif →
  compagnie et aéroports, puis immatriculation → **marque et modèle** de
  l'appareil. Tous les avions n'y sont pas : à défaut, le bandeau affiche le
  code type transmis par l'avion lui-même (`B77W`, `A20N`).
- **[hexdb.io](https://hexdb.io/)** — repli quand adsbdb ne connaît pas la route.
- **[mawaqit.net](https://mawaqit.net/)** — horaires de la mosquée. Leur API
  est privée ; la page publique de chaque mosquée embarque en revanche un objet
  JSON `confData` avec le calendrier annuel complet, adhan et iqama compris.
  C'est ce que lit `prieresource.py`. Rien n'est documenté ni garanti de leur
  côté : si la page change, c'est l'extraction qui casse en premier.

OpenSky a été écarté : depuis mars 2026 il impose un flux OAuth2 et un système
de crédits, sans rien apporter ici.

Les routes sont mises en cache 12 h dans `routes_cache.json`, ce qui réduit
fortement le nombre d'appels à adsbdb. Le calendrier de prière, lui, couvre
l'année entière : il est rechargé une fois par jour dans `prieres_cache.json`,
et le panneau reste juste même si le réseau tombe plusieurs semaines.

## Matériel

| Élément | Choix conseillé |
| --- | --- |
| Panneaux | 2 × HUB75 P4 64×32 **indoor**, scan 1/16 → 128×32 px, 51 × 13 cm |
| Alternative discrète | 2 × P3 64×32 → 38 × 10 cm |
| Microcontrôleur | ESP32 classique ou ESP32-S3 (pas de C3 : pas de DMA parallèle) |
| Alimentation | 5 V / 8 A dédiée, jamais l'USB de l'ESP32 |
| Finition | filtre acrylique fumé gris 3 mm devant le panneau |

Un adaptateur de niveau 3,3 V → 5 V (74HCT245) fiabilise les signaux ; beaucoup
de montages fonctionnent sans, mais c'est la première chose à ajouter en cas
d'instabilité.

### Câblage HUB75 → ESP32

| HUB75 | GPIO | HUB75 | GPIO |
| --- | --- | --- | --- |
| R1 | 25 | A | 23 |
| G1 | 26 | B | 19 |
| B1 | 27 | C | 5 |
| R2 | 14 | D | 17 |
| G2 | 12 | E | 32 |
| B2 | 13 | CLK | 16 |
| LAT | 4 | OE | 15 |

Masse commune entre l'ESP32 et l'alimentation des panneaux.

## Firmware

1. Installer dans l'IDE Arduino :
   - **ESP32 HUB75 LED MATRIX PANEL DMA Display**
   - **Adafruit GFX Library** — dépendance de la précédente, qui tire
     elle-même Adafruit BusIO. Sans elle, la compilation échoue sur
     `Adafruit_GFX.h: No such file or directory`.
   - **ArduinoJson** (v7)
2. Régler **Outils > Partition Scheme > Huge APP (3MB No OTA)**. Avec le
   schéma par défaut le croquis remplit 87 % des 1,3 Mo et il ne reste pas la
   place des logos ; en Huge APP il occupe 36 % de 3,1 Mo.
3. Ouvrir `firmware/panneau_vols.ino`, renseigner `WIFI_SSID`, `WIFI_PASS` et
   `GATEWAY_URL` (l'adresse IP de la machine qui fait tourner `server.py`).
4. Téléverser.

Occupation mesurée avec 60 logos : **36 %** de la mémoire programme et **15 %**
de la SRAM, soit 276 Ko libres pour les variables locales. L'ESP32-S3 compile
aussi (35 %) ; l'ESP32-C3 échoue à l'édition de liens, faute de DMA parallèle
— l'erreur tombe au build, pas au téléversement.

Avant de téléverser, `python3 verif_firmware.py` compile le croquis et signale
les erreurs. Il demande [arduino-cli](https://arduino.github.io/arduino-cli/),
s'ignore s'il ne le trouve pas, et compile une copie temporaire : Arduino veut
un dossier portant le nom du croquis, or le nôtre s'appelle `firmware/`.

Si l'image apparaît décalée d'une colonne, basculez `cfg.clkphase` à `true`.

La police du firmware est générée depuis celle du simulateur :

```bash
python3 export_font.py
```

Relancez cette commande après toute modification de `font5x7.py`, pour que les
deux rendus restent identiques.

## Logos des compagnies

Déposez des PNG carrés nommés par code OACI dans `logos/` (`AFR.png`, `EZY.png`,
`RYR.png`, `BAW.png`, `DLH.png`, `KLM.png`…). Le simulateur les redimensionne en
24×24 si Pillow est installé :

```bash
pip install Pillow
```

Sans logo correspondant, l'affichage retombe sur une silhouette d'avion et le
code de la compagnie — lisible et suffisant au quotidien.

### Sur l'ESP32

Décoder du PNG serait trop lourd. Les images sont donc converties une fois pour
toutes en RGB565 :

```bash
python3 export_logos.py
```

Cela écrit `firmware/logos.h`, qu'il suffit de retéléverser avec le croquis.
Les tableaux y sont `const`, donc rangés **en flash et non en SRAM** : compter
1152 octets de flash par logo, et rien sur les ~200 Ko de SRAM libre.

Le croquis compile sans ce fichier (`#if __has_include`) et affiche alors la
silhouette pour tout le monde. Un logo absent du fichier retombe aussi sur la
silhouette, compagnie par compagnie.

Les pixels noirs sont traités comme transparents, des deux côtés du jumeau :
un PNG à fond transparent donne un logo détouré sur le panneau.

### Ce qui passe et ce qui ne passe pas

24×24 pixels, c'est peu. Les logos à **emblème** ressortent très bien — la grue
de Lufthansa, la harpe de Ryanair, la queue d'Air France. Les **logotypes
textuels** ne survivent pas : « easyJet » ou « British Airways » réduits à cette
taille ne sont qu'une traînée de couleur.

Le rapport largeur/hauteur est conservé et l'image centrée, donc rien n'est
écrasé ; mais un pavillon très allongé finirait à quelques pixels de haut. En
dessous de `LOGO_MIN_PX` (10 px), le logo est écarté et l'affichage retombe sur
la silhouette d'avion plus le code OACI, qui restent lisibles.

Pour écarter un logo qui ne te plaît pas, **supprime simplement son PNG** : le
repli est automatique, compagnie par compagnie, sans rien à configurer.

**Attention** : les logos de compagnies sont des marques déposées. Pour un
montage personnel, aucun souci. Si vous publiez le projet, ne versionnez pas les
images — fournissez un script de conversion et laissez chacun apporter les
siennes.

## Pistes d'évolution

- **Récepteur local** : une clé RTL-SDR (~25 €) et `readsb` sur un Raspberry Pi
  donnent vos propres données ADS-B, sans quota ni latence réseau.
- **Wokwi** : le simulateur en ligne gère HUB75 et le Wi-Fi, ce qui permet de
  valider le croquis complet avant d'avoir le matériel.
- **Mode veille** : couper l'affichage la nuit, ou réduire `BRIGHTNESS` selon
  l'heure.
- **Deuxième rangée** : passer à 128×64 (4 panneaux) pour afficher le type
  d'appareil, l'immatriculation et l'altitude sur des lignes dédiées.
