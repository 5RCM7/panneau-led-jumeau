// ecran_alerte.h - un avion traverse le panneau quand un nouveau vol arrive
//
// Jumeau de ecran_alerte.py, ligne pour ligne. La duree, la silhouette et la
// position doivent garder les memes valeurs que du cote Python.
//
//     ~~~~>                            silhouette, de droite a gauche
//     AVION AU DESSUS                  annonce, centree
//     AFR1234                          indicatif du vol, centre
//
// L'alerte se declenche quand l'indicatif change, des deux cotes du jumeau
// avec la meme regle : la passerelle n'est interrogee que toutes les douze
// secondes et une fenetre de deux secondes lui echapperait.
//
// Inclus depuis panneau_vols.ino APRES les primitives de dessin.

#ifndef ECRAN_ALERTE_H
#define ECRAN_ALERTE_H

// Mise en page - memes valeurs que ecran_alerte.py
static const uint32_t ALERTE_MS = 2200;
static const int16_t AVION_Y = 1;
static const int16_t MOSQUEE_Y = 1;
static const char *ANNONCE = "AVION AU DESSUS";
static const char *ANNONCE_PRIERE = "C'EST L'HEURE";

// Silhouette vue de dessus, nez a gauche, ailes en fleche. Meme motif que du
// cote Python : la bande du haut va de AVION_Y a LINE2_Y, soit dix pixels.
static const int16_t AVION_W = 17;
static const int16_t AVION_H = 9;
static const char *AVION[AVION_H] = {
    "..............#..",
    ".....#.......##..",
    "....##......###..",
    "...###.....####..",
    ".################",
    "...###.....####..",
    "....##......###..",
    ".....#.......##..",
    "..............#..",
};

// Mosquee : coupole, fleche et minaret. Meme motif que du cote Python.
static const int16_t MOSQUEE_W = 17;
static const int16_t MOSQUEE_H = 9;
static const char *MOSQUEE[MOSQUEE_H] = {
    "..............#..",
    ".......#.....###.",
    "......###....###.",
    ".....#####...###.",
    "....#######..###.",
    "...#########.###.",
    "...#########.###.",
    "...#########.###.",
    ".################",
};

static void drawCentre(int16_t y, const char *texte, uint32_t rgb) {
  if (!texte || !texte[0]) return;
  int16_t x = (WIDTH_PX - textWidth(texte)) / 2;
  drawText(x, y, texte, rgb, 0, WIDTH_PX - 1);
}

// Abscisse de la silhouette. Lineaire : un avion garde sa vitesse, et
// l'adoucissement des transitions n'aurait pas de sens ici.
static int16_t positionAvion(float avancement) {
  float t = avancement < 0.0f ? 0.0f : (avancement > 1.0f ? 1.0f : avancement);
  return (int16_t)lroundf(WIDTH_PX + (-AVION_W - WIDTH_PX) * t);
}

// Abscisse de la mosquee : elle entre par la droite et se pose au centre.
// Adoucie, contrairement a l'avion : celui-ci traverse a vitesse constante,
// celle-la arrive et s'arrete, donc elle freine.
static int16_t positionMosquee(float avancement) {
  int16_t arrivee = (WIDTH_PX - MOSQUEE_W) / 2;
  return (int16_t)lroundf(WIDTH_PX + (arrivee - WIDTH_PX) * adoucis(avancement));
}

static void drawSpriteClip(const char **motif, int16_t hauteur,
                           int16_t largeur, int16_t x0, int16_t y0,
                           uint32_t rgb, int16_t clipL, int16_t clipR) {
  for (int16_t ligne = 0; ligne < hauteur; ligne++) {
    for (int16_t colonne = 0; colonne < largeur; colonne++) {
      if (motif[ligne][colonne] != '#') continue;
      int16_t p = x0 + colonne;
      if (p < clipL || p > clipR) continue;
      px(p, y0 + ligne, rgb);
    }
  }
}

static void drawSprite(const char **motif, int16_t hauteur, int16_t largeur,
                       int16_t x0, int16_t y0, uint32_t rgb) {
  drawSpriteClip(motif, hauteur, largeur, x0, y0, rgb, 0, WIDTH_PX - 1);
}

// N'effacent pas l'ecran : l'appelant s'en charge, cf. panneau_vols.ino.
static void renderAlerte(const Flight &f, float avancement) {
  drawSprite(AVION, AVION_H, AVION_W, positionAvion(avancement), AVION_Y,
             RGB_TEXTE);
  drawCentre(LINE2_Y, ANNONCE, RGB_PRINCIPAL);
  drawCentre(LINE3_Y, f.callsign, RGB_ACCENT);
}

static void renderAlertePriere(const Prieres &p, float avancement) {
  drawSprite(MOSQUEE, MOSQUEE_H, MOSQUEE_W, positionMosquee(avancement),
             MOSQUEE_Y, RGB_TEXTE);
  drawCentre(LINE2_Y, ANNONCE_PRIERE, RGB_PRINCIPAL);
  drawCentre(LINE3_Y, p.nom, RGB_ACCENT);
}

#endif  // ECRAN_ALERTE_H
