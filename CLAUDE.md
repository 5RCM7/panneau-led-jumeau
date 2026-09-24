# Panneau LED « gare » — vols au-dessus de la maison

Panneau LED 128×32 façon affichage de gare. Huit scènes en rotation, chacune
avec sa durée : le vol qui passe au-dessus de la maison (indicatif, compagnie,
origine → destination), la prochaine prière de la mosquée, le bandeau des cinq
horaires du jour, les annonces de la mosquée, la météo, le nom d'Allah du
jour, le quota Claude Code, et l'heure. Une prière qui prend la main passe
devant tout, et les arrivées sont annoncées.

Le projet est un **jumeau numérique** : un simulateur PC et un vrai panneau
HUB75 piloté par ESP32 affichent exactement la même chose. C'est la contrainte
centrale du dépôt — voir « Règle du jumeau » plus bas.

## Commandes

Le dépôt est dans `jumeau/`, ce fichier est un cran au-dessus.

```bash
python3 server.py            # passerelle + simulateur, http://localhost:8080
python3 test_hors_ligne.py   # 341 vérifications, aucun réseau requis
python3 verif_annonce.py     # annonce d'avion, Python contre C compilé (si g++)
python3 apercu.py [secondes] # rend apercu.png sans lancer le serveur
python3 apercu_html.py       # rend apercu.html, les vingt scènes
python3 export_font.py       # régénère firmware/font5x7.h depuis font5x7.py
python3 export_logos.py      # convertit logos/*.png en firmware/logos.h
python3 export_arabe.py      # regenere les noms de prieres en arabe
python3 export_adkar.py      # regenere les 99 noms d'Allah
python3 maj_usage.py ...     # releve /usage -> usage.json
python3 verif_firmware.py    # compile le croquis ESP32 (si arduino-cli)
```

Pas de dépendances à installer : bibliothèque standard uniquement. Pillow est
optionnel, et sert seulement à charger les logos PNG dans le simulateur.

`verif_firmware.py` compile le croquis sans le téléverser. **Le test hors
ligne ne voit pas la syntaxe C** : il compare des valeurs, pas du code. Sans
cette étape, une erreur de compilation ne se découvre qu'au téléversement.
Il s'ignore si arduino-cli n'est pas installé, et compile une copie temporaire
parce qu'Arduino exige un dossier portant le nom du croquis, alors que le
nôtre s'appelle `firmware/`.

`test_hors_ligne.py` sort en code 1 si une vérification échoue. Lance-le après
toute modification de `font5x7.py`, d'un `ecran_*.py`, de `panel.py`,
`transitions.py`, `flightsource.py` ou `horaires.py` — et après toute retouche
d'un fichier du `firmware/`, puisqu'il compare les constantes des deux côtés.

## Architecture

Neuf écrans : `vol`, `priere`, `horaires`, `meteo`, `heure`, les trois
annonces et la veille. Les cinq premiers tournent, les autres s'intercalent.
`heure` est toujours disponible : il ne dépend d'aucune source réseau.

**L'heure figure sur chaque écran de la rotation et sur la veille**, jamais
sur une annonce : le panneau est une horloge murale avant d'être un afficheur
de vols. Elle vient toujours de la passerelle, jamais de l'ESP32. En ajoutant
un écran, lui réserver une place pour l'heure.

```
adsb.lol      (positions)  ─┐
adsbdb.com    (routes)      ├─▶ flightsource.py ──┐
adsbdb.com    (appareils)   │                     │
hexdb.io      (repli)      ─┘                     │
                                                  │
mawaqit.net   (confData)   ──▶ prieresource.py ───┤
                                 └─▶ horaires.py  ├─▶ passerelle.py
                                                  │      (rotation,
open-meteo.com (temps)     ──▶ meteosource.py ────┘       annonces)
                                                            │
                                                            ▼
                                                         server.py
                                                      ┌─────┴─────┐
                                                simulateur      ESP32
```

| Fichier | Rôle |
| --- | --- |
| `font5x7.py` | police bitmap 5×7 — **source unique de vérité** |
| `panel.py` | Frame, primitives de dessin, écran des vols |
| `ecran_prieres.py` | écran des horaires de prière |
| `ecran_horaires.py` | tableau des cinq horaires du jour |
| `ecran_alerte.py` | annonces : avion qui traverse, mosquée qui se pose |
| `transitions.py` | roulement vertical entre deux écrans |
| `ecran_meteo.py` | écran météo et son annonce |
| `ecran_heure.py` | écran de l'heure, et format de la date |
| `ecran_adkar.py` | écran adkar : le nom d'Allah du jour |
| `ecran_claude.py` | écran Claude Code : étoile animée et quota |
| `ecran_annonces.py` | bandeau des annonces de la mosquée |
| `annonces.py` | annonces lues dans le confData, filtrées et nettoyées |
| `ecran_liaison.py` | écran de liaison perdue |
| `audio.py` | quel son jouer, à quel volume — **la politique** |
| `claudesource.py` | lecture d'`usage.json`, calcul de ce qui reste |
| `maj_usage.py` | écrit `usage.json` depuis les chiffres de `/usage` |
| `icones_meteo.py` | les sept silhouettes météo |
| `arabe.py` | noms de prières en arabe, **généré** |
| `export_arabe.py` | génère `arabe.py` et `firmware/arabe.h` |
| `adkar_source.py` | **contenu** des 99 noms : c'est ici qu'on corrige |
| `adkar.py` | 99 noms en silhouettes, **généré** |
| `export_adkar.py` | génère `adkar.py` et `firmware/adkar.h` |
| `cadre.py` | tampon de pixels et primitives de dessin |
| `meteosource.py` | appel et cache d'Open-Meteo |
| `passerelle.py` | sondage des sources, rotation, annonces |
| `composition.py` | charge utile ESP32 et composition de l'image |
| `verif_jumeau.py` | comparaison automatique Python / C |
| `verif_annonce.py` | annonce d'avion : scénario rejoué côté Python et côté C |
| `verif_firmware.py` | compile le croquis ESP32 |
| `echantillons.py` | jeux d'essai des tests |
| `apercu_scenes.py` | table des scènes de l'aperçu |
| `flightsource.py` | appels APIs, choix de l'avion, cache des routes |
| `prieresource.py` | récupération et cache du confData Mawaqit |
| `horaires.py` | lecture du calendrier, choix de la prière à afficher |
| `server.py` | passerelle HTTP, arbitrage des écrans, page de simulation |
| `apercu_html.py` | génère `apercu.html` depuis le moteur de rendu |
| `export_font.py` | génère `firmware/font5x7.h` |
| `export_logos.py` | génère `firmware/logos.h` depuis `logos/*.png` |
| `firmware/panneau_vols.ino` | croquis Arduino ESP32 |
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
| `firmware/audio.h` | pilote DFPlayer Mini, câblage documenté dedans |
| `firmware/icones_meteo.h` | silhouettes météo côté firmware |
| `firmware/arabe.h` | **généré** — ne jamais éditer à la main |
| `firmware/adkar.h` | **généré** — ne jamais éditer à la main |
| `firmware/ecran_vol.h` | écran des vols côté firmware |
| `firmware/annonce_vol.h` | règle d'annonce d'avion, sans dépendance Arduino |
| `firmware/passerelle.h` | client HTTP côté firmware |
| `firmware/font5x7.h` | **généré** — ne jamais éditer à la main |
| `firmware/logos.h` | **généré**, non versionné (marques déposées) |
| `test_hors_ligne.py` | tests avec réponses au format réel des APIs |

Endpoints : `/` (simulateur), `/flight` (JSON compact ESP32, ~470 octets avec
vol, prière, journée, météo et heure), `/flight/full`, `/prieres`, `/meteo`,
`/frame`, `/snapshot.png`.

**La rotation des écrans est faite dans `passerelle.py`** et transmise dans
le champ `sc`. Chaque écran a sa durée propre (`duree_ecrans`), les écrans
indisponibles sont sautés. Le firmware obéit, il ne rejoue pas la règle. Ne
pas dupliquer cette logique côté C — il garde seulement des garde-fous si la
passerelle devient injoignable.

**L'audio suit la même règle.** `audio.py` décide quel son, à quel volume,
et sous quelle clé ; le firmware joue quand la clé change, et rien d'autre.
Ne pas déplacer cette décision côté C : elle est testable en Python, elle ne
l'est pas dans le croquis.

**La prière courante se recalcule à chaque demande** (`current_prieres`),
elle n'est pas gardée depuis le dernier sondage. Le réseau reste à la
cadence de `_prieres_step`, mais le franchissement d'heure doit être exact :
l'adhan sonne dessus. Ne pas « optimiser » en remettant un instantané.

**Une seule exception**, `ecran_liaison` : le firmware l'impose de lui-même
contre le champ `sc`, après `LIAISON_SEUIL_MS` sans réponse. La passerelle ne
peut pas signaler son propre silence, et l'ESP32 n'ayant pas d'horloge,
l'heure affichée se fige avec le reste. Les écrans de ce genre sont listés
dans `composition.ECRANS_LOCAUX`.

Ordre de priorité : adhan et iqama d'abord, puis les écrans de prière qu'un
avion **ne doit jamais interrompre** (`ECRANS_PRIERE`), puis l'annonce
d'arrivée d'un avion, puis la rotation. Sur une horloge murale, l'heure de la
prière passe avant l'avion qui traverse.

`POLL_MS` est à 3 s côté firmware, et non 12 : c'est une requête sur le réseau
local, gratuite, et il faut suivre une rotation de 30 s. Ce sont `poll_seconds`
et les caches qui ménagent les APIs publiques, pas la cadence de l'ESP32.

**Les trois annonces sont la seule exception**, et délibérément : elles durent
2,2 s alors que l'ESP32 n'interroge la passerelle que toutes les 3 s, donc il
pourrait les manquer. Chaque côté les déclenche lui-même, avec la même règle et
la même durée : changement d'indicatif pour l'avion, changement de prière
prenant la main pour la mosquée, arrivée du tour pour la météo.

L'annonce d'avion part **au premier passage de `sc` à `vol` avec un nouvel
indicatif**, pas à l'arrivée de l'avion : pendant un écran de prière la
passerelle le fait attendre, et le firmware doit attendre avec elle. La règle
C vit dans `firmware/annonce_vol.h`, que `verif_annonce.py` compile sur le PC
pour rejouer le même scénario que la passerelle.

L'avion affiché garde l'écran tant qu'il reste dans le rayon, sauf si un autre
est plus proche de `bascule_km` (1 km par défaut) : sans cette hystérésis,
deux avions qui se croisent se relaient à chaque sondage et relancent
l'annonce à chaque fois.

Le champ `sc` porte toujours l'**écran de fond**, jamais le nom d'une annonce :
le firmware ne connaît que `vol`, `priere`, `horaires` et `meteo`, et
retomberait en veille sur un nom qu'il ne sait pas lire. Voir `ECRAN_DE_FOND`
dans `composition.py`, et le test qui le vérifie.

## Règle du jumeau

Cinq choses sont **partagées**, pas seulement similaires, entre les fichiers
Python de rendu et leurs jumeaux C. Toute modification de l'une impose la même
de l'autre, dans le même commit :

| Python | C |
| --- | --- |
| `panel.py` | `firmware/panneau_vols.ino` |
| `ecran_prieres.py` | `firmware/ecran_prieres.h` |
| `transitions.py` | `firmware/transitions.h` |
| `ecran_alerte.py` | `firmware/ecran_alerte.h` |
| `ecran_horaires.py` | `firmware/ecran_horaires.h` |
| `ecran_meteo.py` | `firmware/ecran_meteo.h` |
| `icones_meteo.py` | `firmware/icones_meteo.h` |
| `ecran_heure.py` | `firmware/ecran_heure.h` |
| `arabe.py` | `firmware/arabe.h` (générés ensemble) |
| `ecran_adkar.py` | `firmware/ecran_adkar.h` |
| `ecran_claude.py` | `firmware/ecran_claude.h` |
| `ecran_annonces.py` | `firmware/ecran_annonces.h` |
| `ecran_liaison.py` | `firmware/ecran_liaison.h` |
| `audio.py` | `firmware/audio.h` (constantes seulement) |
| `adkar.py` | `firmware/adkar.h` (générés ensemble) |

1. **La police.** `font5x7.py` est la source. Après modification, relancer
   `python3 export_font.py`. Ne jamais éditer `firmware/font5x7.h` directement.
2. **La mise en page.** `LOGO_X0/X1`, `SEP_X`, `TEXT_X0/X1`, `LINE1_Y`,
   `LINE2_Y`, `LINE3_Y`, `SCROLL_PX_PER_SEC`, `SCROLL_GAP` pour l'écran des
   vols ; `PRIERE_X0/X1`, `PRIERE_RULE_Y` pour celui des prières ;
   `HORAIRES_X0/X1`, `HORAIRES_COL2` et les abrégés pour le tableau ;
   `AVION_*`, `MOSQUEE_*` et les textes pour les annonces ; `METEO_*` et les
   sept silhouettes pour la météo ; `HEURE_ECHELLE`, `HEURE_Y` et `DATE_Y`
   pour l'heure ; `ADKAR_X0/X1`, `ADKAR_ENTETE_Y`, `ADKAR_MOT_Y`,
   `ADKAR_SENS_Y`, `ADKAR_PX_PAR_SEC`, `ADKAR_GAP` pour l'écran adkar ;
   `CLAUDE_*` et les huit phases de l'étoile pour l'écran Claude Code ;
   `ANNONCES_*` pour le bandeau de la mosquée ; `LIAISON_*` et ses trois
   textes pour l'écran de liaison perdue. Mêmes valeurs des deux côtés.
3. **L'arabe.** `arabe.py` et `firmware/arabe.h` sont **générés ensemble**
   par `export_arabe.py`, depuis une vraie police. Ne jamais les éditer : la
   police 5×7 ne peut pas rendre l'arabe, qui demande des formes
   contextuelles et une écriture de droite à gauche. Le générateur demande
   `arabic-reshaper` et `python-bidi`, le panneau n'a besoin de rien.
   `adkar.py` et `firmware/adkar.h` suivent la même règle, générés par
   `export_adkar.py` depuis `adkar_source.py` — **c'est ce dernier qu'on
   corrige** quand une translittération ou un sens est à revoir.
4. **Les couleurs.** `TEXTE`, `SECONDAIRE`, `ACCENT`, `PRINCIPAL`, `SEP` en
   Python ; `RGB_TEXTE`, `RGB_SECONDAIRE`, etc. en C. Mêmes valeurs. Les deux
   écrans partagent cette palette : ne pas en ajouter pour un seul des deux.
   Les noms disent un **rôle**, pas une teinte — on peut donc changer la
   palette sans renommer quoi que ce soit.
5. **Les transitions.** `TRANSITION_MS` et la courbe `adoucis()` existent des
   deux côtés avec les mêmes valeurs. Les fonctions de rendu **n'effacent pas
   l'écran** : l'appelant le fait, puis superpose deux écrans décalés. Ne pas
   réintroduire un `clearScreen()` dans un moteur de rendu.

`firmware/ecran_prieres.h` est inclus **au milieu** de `panneau_vols.ino`,
après les primitives de dessin, pour s'en servir sans redéclarer une deuxième
copie des constantes. Ne pas le remonter en tête de fichier.

Si tu changes la mise en page d'un seul côté, le jumeau n'en est plus un et le
projet perd son intérêt. Signale-le plutôt que de laisser diverger.

`verif_jumeau.py` lit les en-têtes C et compare 29 constantes, les 5 couleurs,
les deux silhouettes d'annonce, les sept icônes météo et les trois textes
d'annonce à leurs jumelles Python. Une divergence fait échouer la suite en nommant la constante fautive.
Ajoute les nouvelles constantes partagées à la table `JUMELLES` du test.

## Contraintes matérielles

Chiffres **mesurés** à la compilation (60 logos, schéma Huge APP) : 36 % de la
mémoire programme, 15 % de la SRAM, 276 Ko libres pour les variables locales.
`python3 verif_firmware.py` les recalcule. Garder en tête :

- **Le schéma de partition Huge APP est obligatoire.** Par défaut l'ESP32
  n'offre que 1,3 Mo à l'application, dont le croquis occupe déjà 87 % : il
  resterait 167 Ko, moins que le budget de logos. Huge APP porte la partition
  à 3,1 Mo. C'est un réglage de l'IDE, pas du code, donc rien ne le rappelle
  au téléversement — d'où la mention en tête du croquis.
- **Adafruit GFX** est une dépendance de la bibliothèque HUB75 et doit être
  installée à part, sinon la compilation échoue.

- La luminosité est décidée par la passerelle (champ `br`) et appliquée par
  `setBrightness8()` côté C. **Le simulateur n'applique pas ce niveau tel
  quel** : `Gateway.luminosite_relative()` en fait un rapport. 40 sur 255 est
  un rapport cyclique confortable pour des LED, mais donnerait une image de
  moniteur à 16 %, noire en plein jour. Ne pas « corriger » cela en passant
  `luminosite()` à `attenue()` : c'est exactement le bug qui a été corrigé.
  `apercu.html` ne s'atténue jamais.
- Les bornes `nuit_debut` et `nuit_fin` acceptent une heure pleine, une heure
  `"HH:MM"`, ou `"fajr"` qui suit la première prière du jour. Sans horaires
  disponibles, `"fajr"` retombe sur une heure fixe : un panneau tamisé toute
  la journée serait pire qu'une veille approximative.
- La charge utile `/flight` doit rester sous `composition.BUDGET_OCTETS`,
  **700 octets**. Le plafond était de 400 du temps où seuls les vols
  circulaient ; avec les prières, la journée complète et la météo, le pire cas
  monte à 521 et il a été relevé délibérément. ArduinoJson v7 alloue sur le
  tas : 500 octets de JSON lui coûtent environ 1,5 Ko, sur ~200 Ko de SRAM
  libre. La contrainte réelle n'est pas là. Un test mesure le pire cas.
- Tout texte venu d'une API doit passer par `font5x7.affichable()` **avant**
  d'être envoyé à l'ESP32. La police est ASCII pure ; « São Paulo » ou
  « Nîmes » sortiraient en points d'interrogation, des deux côtés du jumeau.
  Le nettoyage se fait dans `build_flight()`, à la source, pas à l'affichage.
- `Flight.ticker` fait 144 octets côté C. Si `build_ticker()` peut produire plus
  long, il faut agrandir le tampon **et** le seuil du test 12. Pire cas
  mesuré avec l'appareil : 113 caractères, chaque champ rempli jusqu'à son
  tampon C.
- Pas de décodage PNG sur l'ESP32 : `export_logos.py` convertit `logos/*.png`
  en RGB565 dans `firmware/logos.h`. Un en-tête C plutôt que LittleFS comme
  envisagé au départ : les tableaux `const` vont en flash, pas en SRAM, et ça
  évite l'étape de téléversement du système de fichiers. 1152 octets de flash
  par logo, vérifié à la compilation : 60 logos pèsent 69 976 octets. Le
  croquis compile sans le fichier (`#if __has_include`) et retombe alors sur
  la silhouette — les deux chemins sont compilés.
- Les ESP32-C3/C2/C6/H2 ne conviennent pas (pas de DMA parallèle). ESP32
  classique ou S3 uniquement. **Vérifié à la compilation** : le classique
  (36 %) et le S3 (35 %) passent, le C3 échoue à l'édition de liens. L'erreur
  est laide (`collect2.exe: ld returned 1 exit status`) mais elle tombe au
  build, donc on ne peut pas flasher une carte inadaptée par inadvertance.

## Style

- **Commentaires et documentation en français**, sans accents dans le code
  Python et C (les fichiers restent ASCII pur pour éviter les surprises de
  compilation Arduino). Le README et ce fichier peuvent porter les accents.
- Python : bibliothèque standard, pas de framework. `snake_case`. Docstrings
  courtes en tête de fonction quand le nom ne suffit pas.
- C : mêmes noms de constantes que Python mais en `SCREAMING_CASE` avec préfixe
  `RGB_` pour les couleurs.
- `g_screen` doit pouvoir contenir le plus long nom d'écran **et son zéro
  final**. À 8 octets, `"horaires"` était tronqué en `"horaire"`, que
  `ecranDepuisNom()` ne reconnaît pas : le panneau retombait en veille à
  chaque tour du tableau. Il est à 12.
- Pas de fichiers de plus de ~250 lignes : découper plutôt. **Cinq fichiers
  dépassent nettement** et l'écart se creuse à chaque fonctionnalité :
  `test_hors_ligne.py` (522), `server.py` (508), `firmware/panneau_vols.ino`
  (455), `apercu_html.py` (306) et `panel.py` (259). Coupures naturelles :
  sortir `Frame` de `panel.py` dans son propre module en le réexportant ;
  sortir la table des scènes d'`apercu_html.py` ; séparer les jeux d'essai des
  vérifications dans le test ; sortir la rotation et les annonces de
  `server.py`. **C'est le prochain chantier à faire**, hors commit de
  fonctionnalité.
- Les fichiers `.py`, `.ino` et `.h` doivent rester **ASCII pur**, tiret
  cadratin compris. Attention sous Windows : `Set-Content -Encoding utf8`
  ajoute un BOM en PowerShell 5.1, ce qui viole la règle sans prévenir.

## Données et vie privée

- `config.json` contient les **coordonnées GPS du domicile** et la mosquée
  fréquentée. Il est dans `.gitignore` ; `config.exemple.json` porte les mêmes
  clés avec des coordonnées neutres et sert de modèle. Ne jamais publier les
  vraies valeurs, ni les écrire en dur dans le code.
- `routes_cache.json`, `prieres_cache.json` et `apercu.html` sont générés,
  ignorés par git.
- Les logos de compagnies sont des **marques déposées**. `logos/*.png` **et**
  `firmware/logos.h`, qui en dérive, sont dans `.gitignore` : usage personnel
  seulement, jamais versionnés. Ne jamais committer l'un ni l'autre, même
  « juste pour l'exemple ».
- Les APIs utilisées sont gratuites et communautaires. Respecter les cadences :
  `poll_seconds` ≥ 10, cache des routes à 12 h, calendrier de prière à 24 h.
  Ne pas retirer le cache.
- **Mawaqit n'a pas d'API publique** : la leur est privée. On lit l'objet
  `confData` embarqué dans le HTML de la page de la mosquée. Rien n'est
  documenté ni garanti de leur côté, donc `prieresource._extract_conf()` est
  le point de rupture le plus probable du projet. Il est couvert par deux
  tests, dont un sur les accolades à l'intérieur des chaînes.
- Le calendrier Mawaqit couvre l'année entière : un seul appel réseau par jour,
  et l'affichage reste juste des semaines sans réseau. Ne pas transformer ça en
  requête quotidienne par prière.
- OpenSky a été écarté volontairement (OAuth2 + crédits depuis mars 2026). Ne
  pas le réintroduire sans raison explicite.

## Travailler sans avion dans le ciel

Mettre `"demo_mode": true` dans `config.json` : vols, prière, journée
complète et météo fictifs, sans aucun appel réseau. Il doit alimenter les
**six écrans** de la rotation (le septième, Claude Code, dépend d'un relevé
`/usage` et disparaît sans lui) — un test le vérifie, parce que c'est
exactement ce qui s'était perdu en ajoutant la météo. Indispensable pour
travailler la mise en page le soir ou hors couverture. **Toujours remettre
`false`** avant de terminer.

`python3 apercu_html.py` donne les dix-sept scènes dans le navigateur sans attendre
le bon moment de la journée. La page rejoue les pixels produits par `panel.py`
et `ecran_prieres.py` : ne jamais y réécrire le rendu en JavaScript, ce serait
un troisième jumeau à maintenir.

## Pistes ouvertes

- Chourouk : `horaires.day_times()` le calcule déjà, aucun écran ne l'affiche.
- Mode veille nocturne, ou luminosité selon l'heure.
- Passage à 128×64 (4 panneaux) : type d'appareil, immatriculation, altitude.
- Récepteur local RTL-SDR + readsb, pour se passer des APIs.

