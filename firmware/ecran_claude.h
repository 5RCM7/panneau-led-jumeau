// ecran_claude.h - l'etoile qui tourne, et ce qu'il reste de quota
//
// Jumeau d'ecran_claude.py, ligne pour ligne.
//
//     CLAUDE CODE                 23:07     en-tete et heure
//      .@.   5H [######----] 61%  4H25
//     @-*-@  7J [#####-----] 52%  5J7H
//
// L'etoile a onze branches tourne : un onzieme de tour ramene la figure sur
// elle-meme, et huit phases suffisent a boucler sans raccord.
//
// Les jauges montrent ce qui RESTE. Une fenetre dont l'heure de remise a
// zero est passee s'affiche en tirets plutot qu'a zero : on ne sait plus.
//
// Inclus depuis panneau_vols.ino APRES ecran_alerte.h (drawSprite).

#ifndef ECRAN_CLAUDE_H
#define ECRAN_CLAUDE_H

// Mise en page - memes valeurs qu'ecran_claude.py
static const int16_t CLAUDE_X0 = 2;
static const int16_t CLAUDE_X1 = WIDTH_PX - 3;
static const int16_t CLAUDE_ENTETE_Y = 0;
static const int16_t CLAUDE_LOGO_X = 1;
static const int16_t CLAUDE_LOGO_Y = 9;
static const int16_t CLAUDE_LIGNE1_Y = 12;
static const int16_t CLAUDE_LIGNE2_Y = 23;
static const int16_t CLAUDE_CLE_X = 26;
static const int16_t CLAUDE_BARRE_X0 = 40;
static const int16_t CLAUDE_BARRE_X1 = 74;
static const int16_t CLAUDE_BARRE_DY = 1;
static const int16_t CLAUDE_BARRE_H = 5;
static const int16_t CLAUDE_PCT_X1 = 99;
static const int16_t CLAUDE_PHASES = 8;
static const int16_t CLAUDE_LOGO_PX = 21;
static const float CLAUDE_PHASES_PAR_SEC = 6.0f;
static const int16_t CLAUDE_SEUIL_BAS = 20;
static const char *CLAUDE_TITRE = "CLAUDE CODE";
static const char *CLAUDE_INCONNU = "--";

static const char *ETOILE0[CLAUDE_LOGO_PX] = {
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
};
static const char *ETOILE1[CLAUDE_LOGO_PX] = {
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
};
static const char *ETOILE2[CLAUDE_LOGO_PX] = {
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
};
static const char *ETOILE3[CLAUDE_LOGO_PX] = {
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
};
static const char *ETOILE4[CLAUDE_LOGO_PX] = {
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
};
static const char *ETOILE5[CLAUDE_LOGO_PX] = {
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
};
static const char *ETOILE6[CLAUDE_LOGO_PX] = {
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
};
static const char *ETOILE7[CLAUDE_LOGO_PX] = {
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
};

static const char **const ETOILE[CLAUDE_PHASES] = {ETOILE0, ETOILE1, ETOILE2, ETOILE3, ETOILE4, ETOILE5, ETOILE6, ETOILE7};

struct Usage {
  bool ok = false;
  char cleA[4] = "";
  char cleB[4] = "";
  int16_t restantA = -1;  // -1 : fenetre expiree, on ne sait plus
  int16_t restantB = -1;
  char resetA[8] = "";
  char resetB[8] = "";
};

// Vert tant qu'il en reste, orange quand la reserve fond.
static uint32_t claudeCouleurJauge(int16_t restant) {
  if (restant < 0) return RGB_SEP;
  return restant <= CLAUDE_SEUIL_BAS ? RGB_TEXTE : RGB_ACCENT;
}

// Une fenetre : son libelle, sa jauge, ce qu'il reste, et son echeance.
static void claudeLigne(int16_t y, const char *cle, int16_t restant,
                        const char *reset) {
  drawText(CLAUDE_CLE_X, y, cle, RGB_SECONDAIRE, CLAUDE_X0, CLAUDE_X1);

  int16_t large = CLAUDE_BARRE_X1 - CLAUDE_BARRE_X0 + 1;
  int16_t plein = restant < 0 ? 0 : (int16_t)lroundf(large * restant / 100.0f);
  uint32_t couleur = claudeCouleurJauge(restant);
  for (int16_t n = 0; n < large; n++) {
    uint32_t teinte = n < plein ? couleur : RGB_SEP;
    for (int16_t dy = 0; dy < CLAUDE_BARRE_H; dy++)
      px(CLAUDE_BARRE_X0 + n, y + CLAUDE_BARRE_DY + dy, teinte);
  }

  char texte[8];
  if (restant < 0) snprintf(texte, sizeof(texte), "%s", CLAUDE_INCONNU);
  else snprintf(texte, sizeof(texte), "%d%%", restant);
  drawText(CLAUDE_PCT_X1 - textWidth(texte) + 1, y, texte, RGB_PRINCIPAL,
           CLAUDE_X0, CLAUDE_X1);
  if (reset && reset[0])
    drawText(CLAUDE_X1 - textWidth(reset) + 1, y, reset, RGB_SECONDAIRE,
             CLAUDE_X0, CLAUDE_X1);
}

// N'efface pas l'ecran : l'appelant s'en charge, cf. panneau_vols.ino.
static void renderClaude(const Usage &u, const char *heure, uint32_t nowMs) {
  // En-tete : le titre a gauche, l'heure a droite. Le panneau reste une
  // horloge murale, quel que soit l'ecran.
  drawText(CLAUDE_X0, CLAUDE_ENTETE_Y, CLAUDE_TITRE, RGB_SECONDAIRE,
           CLAUDE_X0, CLAUDE_X1);
  if (heure && heure[0])
    drawText(CLAUDE_X1 - textWidth(heure) + 1, CLAUDE_ENTETE_Y, heure,
             RGB_SECONDAIRE, CLAUDE_X0, CLAUDE_X1);

  int16_t n = (int16_t)(nowMs / 1000.0f * CLAUDE_PHASES_PAR_SEC)
      % CLAUDE_PHASES;
  drawSprite(ETOILE[n], CLAUDE_LOGO_PX, CLAUDE_LOGO_PX, CLAUDE_LOGO_X,
             CLAUDE_LOGO_Y, RGB_PRINCIPAL);

  claudeLigne(CLAUDE_LIGNE1_Y, u.cleA, u.restantA, u.resetA);
  claudeLigne(CLAUDE_LIGNE2_Y, u.cleB, u.restantB, u.resetB);
}

#endif  // ECRAN_CLAUDE_H
