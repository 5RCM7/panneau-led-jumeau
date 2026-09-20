// icones_meteo.h - silhouettes meteo 17x9
//
// Jumeau d'icones_meteo.py, motif pour motif. Sept icones suffisent : sur
// dix-sept pixels de large, bruine et pluie fine ne se distinguent pas, et
// le brouillard n'est qu'un nuage.
//
// L'ordre du tableau ICONES fait foi : la passerelle envoie un rang, pas
// un nom, pour economiser des octets dans la charge utile.
//
// Inclus depuis panneau_vols.ino AVANT ecran_meteo.h.

#ifndef ICONES_METEO_H
#define ICONES_METEO_H

static const int16_t ICONE_W = 17;
static const int16_t ICONE_H = 9;

static const char *ICONE_SOLEIL[ICONE_H] = {
    "........#........",
    "....#.......#....",
    ".......###.......",
    "......#####......",
    "..#...#####...#..",
    "......#####......",
    ".......###.......",
    "....#.......#....",
    "........#........",
};

static const char *ICONE_LUNE[ICONE_H] = {
    "......####.......",
    "....###..##......",
    "...###....#......",
    "..####...........",
    "..####...........",
    "..####...........",
    "...###....#......",
    "....###..##......",
    "......####.......",
};

static const char *ICONE_ECLAIRCIE[ICONE_H] = {
    "...#..#..#.......",
    "....####.........",
    "...######...##...",
    "....####..######.",
    "...#..#..########",
    ".........########",
    "........#########",
    ".........#######.",
    ".................",
};

static const char *ICONE_NUAGE[ICONE_H] = {
    ".................",
    ".......####......",
    ".....########....",
    "...###########...",
    "..#############..",
    ".###############.",
    ".###############.",
    "..#############..",
    ".................",
};

static const char *ICONE_PLUIE[ICONE_H] = {
    ".......####......",
    ".....########....",
    "...###########...",
    "..#############..",
    ".###############.",
    "..#############..",
    ".................",
    "...#...#...#...#.",
    "..#...#...#...#..",
};

static const char *ICONE_NEIGE[ICONE_H] = {
    ".......####......",
    ".....########....",
    "...###########...",
    "..#############..",
    ".###############.",
    "..#############..",
    ".................",
    "...#.#...#.#...#.",
    "....#.....#......",
};

static const char *ICONE_ORAGE[ICONE_H] = {
    ".......####......",
    ".....########....",
    "...###########...",
    "..#############..",
    ".###############.",
    "..#############..",
    "......####.......",
    ".....###.........",
    "....##...........",
};

// Meme ordre qu'icones_meteo.ORDRE : soleil lune eclaircie nuage pluie neige orage
static const char **ICONES[] = {
    ICONE_SOLEIL,
    ICONE_LUNE,
    ICONE_ECLAIRCIE,
    ICONE_NUAGE,
    ICONE_PLUIE,
    ICONE_NEIGE,
    ICONE_ORAGE,
};
static const int8_t ICONE_COUNT = 7;

// Repli sur le nuage, comme icones_meteo.icone() cote Python.
static const char **iconePourRang(int8_t rang) {
  if (rang < 0 || rang >= ICONE_COUNT) return ICONE_NUAGE;
  return ICONES[rang];
}

#endif  // ICONES_METEO_H
