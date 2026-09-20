// ecran_vol.h - mise en page de l'ecran des vols
//
// Jumeau de panel.py, ligne pour ligne. Les constantes de position vivent
// dans panneau_vols.ino, qui inclut ce fichier apres les avoir declarees.
//
//     [logo] | AFR1234        FL340
//            | CDG -> JFK
//            | AIR FRANCE -> NEW YORK -> 4 KM
//
// Inclus depuis panneau_vols.ino APRES les primitives de dessin.

#ifndef ECRAN_VOL_H
#define ECRAN_VOL_H

// ------------------------------------------------------------------ logos
// Meme zone et meme position que _draw_logo() dans panel.py : bitmap 24x24
// pose en (3, 4), sinon silhouette d'avion et code OACI centre.
static void drawLogo(const Flight &f) {
#ifdef AVEC_LOGOS
  const uint16_t *bitmap = logoFor(f.icao);
  if (bitmap) {
    for (int16_t row = 0; row < LOGO_H; row++) {
      for (int16_t col = 0; col < LOGO_W; col++) {
        uint16_t c = bitmap[row * LOGO_W + col];
        if (!c) continue;  // noir = transparent, comme dans panel.py
        uint8_t r = (c >> 11) & 0x1F, v = (c >> 5) & 0x3F, b = c & 0x1F;
        px(3 + col, 4 + row,
           ((uint32_t)((r << 3) | (r >> 2)) << 16) |
           ((uint32_t)((v << 2) | (v >> 4)) << 8) |
           ((b << 3) | (b >> 2)));
      }
    }
    return;
  }
#endif
  drawChar(12, 5, FONT_PLANE, RGB_SECONDAIRE, 0, LOGO_X1);
  if (f.icao[0]) {
    int16_t x = LOGO_X0 + (LOGO_X1 - LOGO_X0 + 1 - textWidth(f.icao)) / 2;
    drawText(x, 17, f.icao, RGB_TEXTE, 0, LOGO_X1);
  }
}

// ------------------------------------------------------------ composition
// Ces fonctions n'effacent pas l'ecran : c'est l'appelant qui le fait, une
// seule fois, pour pouvoir superposer deux ecrans pendant une transition.
static void renderIdle(const char *heure) {
  drawText(6, LINE1_Y + 4, "CIEL DEGAGE", RGB_SECONDAIRE, 0, WIDTH_PX - 1);
  drawText(6, LINE3_Y - 3, heure, RGB_TEXTE, 0, WIDTH_PX - 1);
}

static void renderFlight(const Flight &f, uint32_t nowMs, const char *heure) {
  for (int16_t y = 2; y <= PANEL_H - 3; y++) px(SEP_X, y, RGB_SEP);

  drawLogo(f);

  // Ligne 1 : indicatif du vol, niveau de vol aligne a droite
  drawText(TEXT_X0, LINE1_Y, f.callsign, RGB_PRINCIPAL, TEXT_X0, TEXT_X1);
  if (f.level[0]) {
    int16_t x = TEXT_X1 - textWidth(f.level) + 1;
    drawText(x, LINE1_Y, f.level, RGB_SECONDAIRE, TEXT_X0, TEXT_X1);
  }

  // Ligne 2 : origine, fleche, destination
  char route[20];
  snprintf(route, sizeof(route), "%s %c %s", f.from[0] ? f.from : "???",
           FONT_ARROW, f.to[0] ? f.to : "???");
  drawText(TEXT_X0, LINE2_Y, route, RGB_ACCENT, TEXT_X0, TEXT_X1);
  // L'heure va sur cette ligne : la premiere est pleine, indicatif et niveau
  // de vol n'y laissent que 23 pixels alors qu'il en faut 29.
  if (heure && heure[0])
    drawText(TEXT_X1 - textWidth(heure) + 1, LINE2_Y, heure, RGB_SECONDAIRE,
             TEXT_X0, TEXT_X1);

  // Ligne 3 : bandeau, defilant s'il depasse la largeur disponible
  int16_t w = textWidth(f.ticker);
  if (w <= TEXT_W) {
    drawText(TEXT_X0, LINE3_Y, f.ticker, RGB_TEXTE, TEXT_X0, TEXT_X1);
  } else {
    int16_t span = w + SCROLL_GAP;
    int16_t off = (int16_t)fmodf(nowMs / 1000.0f * SCROLL_PX_PER_SEC, span);
    drawText(TEXT_X0 - off, LINE3_Y, f.ticker, RGB_TEXTE, TEXT_X0, TEXT_X1);
    drawText(TEXT_X0 - off + span, LINE3_Y, f.ticker, RGB_TEXTE, TEXT_X0,
             TEXT_X1);
  }
}


#endif  // ECRAN_VOL_H
