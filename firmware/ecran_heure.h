// ecran_heure.h - l'heure, et rien d'autre
//
// Jumeau d'ecran_heure.py, ligne pour ligne.
//
//          22:33            heure a l'echelle 3, centree
//      VENDREDI 19 SEPT     date du jour, centree
//
// L'heure et la date viennent de la passerelle : l'ESP32 n'a ni horloge
// sauvegardee ni client NTP, c'est le meme choix que pour l'ecran des prieres.
//
// Inclus depuis panneau_vols.ino APRES les primitives de dessin.

#ifndef ECRAN_HEURE_H
#define ECRAN_HEURE_H

// Mise en page - memes valeurs qu'ecran_heure.py
static const int16_t HEURE_ECHELLE = 3;
static const int16_t HEURE_Y = 1;
static const int16_t DATE_Y = 24;

struct Heure {
  bool ok = false;
  char heure[8] = "";
  char date[20] = "";
};

// Texte agrandi : chaque pixel de la police devient un carre. Pas
// d'interpolation, a dessein : sur un panneau LED, un gros chiffre net vaut
// mieux qu'un gros chiffre flou.
static void drawTextEchelleClip(int16_t x, int16_t y, const char *texte,
                                uint32_t rgb, int16_t echelle, int16_t clipL,
                                int16_t clipR) {
  int16_t curseur = x;
  for (const char *p = texte; *p; ++p) {
    const uint8_t *glyph = fontGlyph(*p);
    for (uint8_t ligne = 0; ligne < FONT_HEIGHT; ligne++) {
      uint8_t bits = glyph[ligne];
      if (!bits) continue;
      for (uint8_t colonne = 0; colonne < FONT_WIDTH; colonne++) {
        if (!(bits & (0x10 >> colonne))) continue;
        for (int16_t dx = 0; dx < echelle; dx++) {
          int16_t q = curseur + colonne * echelle + dx;
          if (q < clipL || q > clipR) continue;
          for (int16_t dy = 0; dy < echelle; dy++)
            px(q, y + ligne * echelle + dy, rgb);
        }
      }
    }
    curseur += FONT_ADVANCE * echelle;
  }
}

static void drawTextEchelle(int16_t x, int16_t y, const char *texte,
                            uint32_t rgb, int16_t echelle) {
  drawTextEchelleClip(x, y, texte, rgb, echelle, 0, WIDTH_PX - 1);
}

static int16_t largeurEchelle(const char *texte, int16_t echelle) {
  size_t n = strlen(texte);
  return n ? (int16_t)(n * FONT_ADVANCE * echelle - echelle) : 0;
}

// N'efface pas l'ecran : l'appelant s'en charge, cf. panneau_vols.ino.
static void renderHeure(const Heure &h) {
  int16_t x = (WIDTH_PX - largeurEchelle(h.heure, HEURE_ECHELLE)) / 2;
  drawTextEchelle(x, HEURE_Y, h.heure, RGB_PRINCIPAL, HEURE_ECHELLE);
  drawCentre(DATE_Y, h.date, RGB_SECONDAIRE);
}

#endif  // ECRAN_HEURE_H
