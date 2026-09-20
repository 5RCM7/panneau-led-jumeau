"""Ecran Claude Code : l'etoile qui tourne, et ce qu'il reste de quota.

    CLAUDE CODE                 23:07     en-tete et heure
     .@.   5H [######----] 61%  4H25
    @-*-@  7J [#####-----] 52%  5J7H

L'etoile a onze branches tourne : onze branches, donc un onzieme de tour
ramene la figure sur elle-meme, et huit phases suffisent a boucler sans
raccord. C'est la seule animation permanente du panneau, tenue lente a
dessein.

Les jauges montrent ce qui RESTE, pas ce qui est consomme : c'est ce qu'on
regarde en passant devant. Une fenetre dont l'heure de remise a zero est
passee s'affiche en tirets plutot qu'a zero, parce qu'on ne sait plus.

Les chiffres viennent d'usage.json, cf. claudesource.py : ni l'ESP32 ni la
passerelle ne savent les demander a Anthropic.

Jumeau de firmware/ecran_claude.h.
"""

import cadre
import font5x7
import panel
from panel import ACCENT, PRINCIPAL, SECONDAIRE, SEP, TEXTE, WIDTH

# Mise en page - memes valeurs dans firmware/ecran_claude.h
CLAUDE_X0 = 2
CLAUDE_X1 = WIDTH - 3
CLAUDE_ENTETE_Y = 0
CLAUDE_LOGO_X = 1
CLAUDE_LOGO_Y = 9
CLAUDE_LIGNE1_Y = 12
CLAUDE_LIGNE2_Y = 23
CLAUDE_CLE_X = 26          # les deux libelles, 5H et 7J
CLAUDE_BARRE_X0 = 40
CLAUDE_BARRE_X1 = 74
CLAUDE_BARRE_DY = 1        # la jauge s'inscrit dans la hauteur d'une ligne
CLAUDE_BARRE_H = 5
CLAUDE_PCT_X1 = 99         # fin du pourcentage, aligne a droite
CLAUDE_PHASES = 8
CLAUDE_LOGO_PX = 21
CLAUDE_PHASES_PAR_SEC = 6.0
CLAUDE_SEUIL_BAS = 20      # en dessous, la jauge passe a l'orange
TITRE = "CLAUDE CODE"
INCONNU = "--"

ETOILE = (
    (
        ".....................",
        ".........#....#......",
        ".........#....#......",
        "....#....#...#.......",
        ".....#...#..##.......",
        ".....##..##.##...##..",
        "......##.####..###...",
        ".#.....##########....",
        "..########.####......",
        "....#####...###......",
        ".......#.....########",
        "....#####...###......",
        "..########.####......",
        ".#.....##########....",
        "......##.####..###...",
        ".....##..##.##...##..",
        ".....#...#..##.......",
        "....#....#...#.......",
        ".........#....#......",
        ".........#....#......",
        ".....................",
    ),
    (
        ".....................",
        ".........#...........",
        "....#....##...#......",
        ".....#...##...#......",
        ".....##..##..##......",
        "......##.##.##.......",
        "......#####.##..###..",
        ".####..######.###....",
        "...#######.#####.....",
        ".....####...##.......",
        "......##.....######..",
        "...######...########.",
        ".#####.###.####......",
        "......##########.....",
        ".....###.####.###....",
        ".....##.##.##...##...",
        "....#...##..##....#..",
        "...#....##..##.......",
        "........#....#.......",
        "........#....#.......",
        ".....................",
    ),
    (
        "..........#..........",
        "..........#..........",
        ".....#....#....#.....",
        ".....##...#...##.....",
        "......##..#..##......",
        "......##..#..##......",
        ".##....#######....##.",
        "...###.#######.###...",
        "....######.######....",
        "......###...###......",
        ".....###.....###.....",
        ".########...########.",
        ".......###.###.......",
        "......#########......",
        ".....##.##.##.##.....",
        "....##..##.##..##....",
        "...#....##.##....#...",
        "........#...#........",
        "........#...#........",
        ".......#.....#.......",
        ".....................",
    ),
    (
        ".....................",
        "...........#.........",
        "......#...##....#....",
        "......#...##...#.....",
        "......##..##..##.....",
        ".......##.##.##......",
        "..###..##.#####......",
        "....###.######..####.",
        ".....#####.#######...",
        ".......##...####.....",
        "..######.....##......",
        ".########...######...",
        "......####.###.#####.",
        ".....##########......",
        "....###.####.###.....",
        "...##...##.##.##.....",
        "..#....##..##...#....",
        ".......##..##....#...",
        ".......#....#........",
        ".......#....#........",
        ".....................",
    ),
    (
        ".....................",
        "......#....#.........",
        "......#....#.........",
        ".......#...#....#....",
        ".......##..#...#.....",
        "..##...##.##..##.....",
        "...###..####.##......",
        "....##########.....#.",
        "......####.########..",
        "......###...#####....",
        "########.....#.......",
        "......###...#####....",
        "......####.########..",
        "....##########.....#.",
        "...###..####.##......",
        "..##...##.##..##.....",
        ".......##..#...#.....",
        ".......#...#....#....",
        "......#....#.........",
        "......#....#.........",
        ".....................",
    ),
    (
        ".....................",
        ".......#....#........",
        ".......#....#........",
        ".......##..##....#...",
        "..#....##..##...#....",
        "...##...##.##.##.....",
        "....###.####.###.....",
        ".....##########......",
        "......####.###.#####.",
        ".########...######...",
        "..######.....##......",
        ".......##...####.....",
        ".....#####.#######...",
        "....###.######..####.",
        "..###..##.#####......",
        ".......##.##.##......",
        "......##..##..##.....",
        "......#...##...#.....",
        "......#...##....#....",
        "...........#.........",
        ".....................",
    ),
    (
        ".....................",
        ".......#.....#.......",
        "........#...#........",
        "........#...#........",
        "...#....##.##....#...",
        "....##..##.##..##....",
        ".....##.##.##.##.....",
        "......#########......",
        ".......###.###.......",
        ".########...########.",
        ".....###.....###.....",
        "......###...###......",
        "....######.######....",
        "...###.#######.###...",
        ".##....#######....##.",
        "......##..#..##......",
        "......##..#..##......",
        ".....##...#...##.....",
        ".....#....#....#.....",
        "..........#..........",
        "..........#..........",
    ),
    (
        ".....................",
        "........#....#.......",
        "........#....#.......",
        "...#....##..##.......",
        "....#...##..##....#..",
        ".....##.##.##...##...",
        ".....###.####.###....",
        "......##########.....",
        ".#####.###.####......",
        "...######...########.",
        "......##.....######..",
        ".....####...##.......",
        "...#######.#####.....",
        ".####..######.###....",
        "......#####.##..###..",
        "......##.##.##.......",
        ".....##..##..##......",
        ".....#...##...#......",
        "....#....##...#......",
        ".........#...........",
        ".....................",
    ),
)


def phase(elapsed):
    """Numero de phase de l'etoile a cet instant."""
    return int(elapsed * CLAUDE_PHASES_PAR_SEC) % CLAUDE_PHASES


def couleur_jauge(restant):
    """Vert tant qu'il en reste, orange quand la reserve fond."""
    if restant is None:
        return SEP
    return TEXTE if restant <= CLAUDE_SEUIL_BAS else ACCENT


def _ligne(frame, y, cle, restant, reset, clip):
    """Une fenetre : son libelle, sa jauge, ce qu'il reste, et son echeance."""
    frame.draw_text(CLAUDE_CLE_X, y, cle, SECONDAIRE, clip)

    # La jauge se remplit de ce qui RESTE, de gauche a droite
    large = CLAUDE_BARRE_X1 - CLAUDE_BARRE_X0 + 1
    plein = 0 if restant is None else int(round(large * restant / 100.0))
    couleur = couleur_jauge(restant)
    for n in range(large):
        teinte = couleur if n < plein else SEP
        for dy in range(CLAUDE_BARRE_H):
            frame.set(CLAUDE_BARRE_X0 + n, y + CLAUDE_BARRE_DY + dy, teinte)

    texte = INCONNU if restant is None else "%d%%" % restant
    cadre.droite(frame, CLAUDE_PCT_X1, y, texte, PRINCIPAL, clip)
    if reset:
        cadre.droite(frame, CLAUDE_X1, y, reset, SECONDAIRE, clip)


def render(usage, elapsed=0.0, heure=None, frame=None):
    """Compose l'ecran Claude Code.

    usage : dict rendu par claudesource.poll(), ou None pour la veille.
    elapsed : secondes ecoulees, pilote la rotation de l'etoile.
    """
    if not usage:
        return panel.render(None, frame=frame, heure=heure)

    if frame is None:
        frame = panel.Frame()
    clip = (CLAUDE_X0, CLAUDE_X1)

    # En-tete : le titre a gauche, l'heure a droite. Le panneau reste une
    # horloge murale, quel que soit l'ecran.
    frame.draw_text(CLAUDE_X0, CLAUDE_ENTETE_Y, TITRE, SECONDAIRE, clip)
    cadre.droite(frame, CLAUDE_X1, CLAUDE_ENTETE_Y, heure or "", SECONDAIRE,
                 clip)

    frame.draw_sprite(CLAUDE_LOGO_X, CLAUDE_LOGO_Y, ETOILE[phase(elapsed)],
                      PRINCIPAL)

    _ligne(frame, CLAUDE_LIGNE1_Y, usage["cle_a"], usage["restant_a"],
           usage["reset_a"], clip)
    _ligne(frame, CLAUDE_LIGNE2_Y, usage["cle_b"], usage["restant_b"],
           usage["reset_b"], clip)
    return frame
