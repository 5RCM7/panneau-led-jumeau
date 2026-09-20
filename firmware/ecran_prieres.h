// ecran_prieres.h - deuxieme mise en page du panneau : horaires de priere
//
// Jumeau de ecran_prieres.py, ligne pour ligne. Les constantes ci-dessous
// doivent garder les memes valeurs que du cote Python.
//
//     MOSQUEE                    21:04      en-tete, mosquee et heure
//     ----------------------------------    filet de separation
//     MAGHREB                    19:59      priere et heure de l'adhan
//     IQAMA 20:09               12 MIN      iqama et temps restant
//
// Ce fichier est inclus depuis panneau_vols.ino APRES les primitives de
// dessin (px, drawText, textWidth) et les constantes de mise en page, car il
// s'en sert sans les redeclarer : une seule definition de chaque valeur, donc
// aucun risque de derive entre les deux ecrans.

#ifndef ECRAN_PRIERES_H
#define ECRAN_PRIERES_H

// Mise en page - memes valeurs que ecran_prieres.py
static const int16_t PRIERE_X0 = 2;
static const int16_t PRIERE_X1 = WIDTH_PX - 3;
static const int16_t PRIERE_RULE_Y = 9;

struct Prieres {
  bool ok = false;
  char nom[12] = "";
  char adhan[8] = "";
  char iqama[8] = "";
  char restant[12] = "";
  char mosquee[12] = "";
  char heure[8] = "";
  bool priseMain = false;
  bool enCours = false;
  bool demain = false;
  // Journee complete pour l'ecran des horaires : cinq HH:MM separes par des
  // virgules, le rang de la priere a venir, et le drapeau du vendredi.
  char horaires[32] = "";
  int8_t rang = -1;
  bool joumoua = false;
  // Titres des annonces de la mosquee, separes par '|', cf. ecran_annonces.h
  char annonces[152] = "";
};

static void drawRight(int16_t y, const char *text, uint32_t rgb) {
  if (!text || !text[0]) return;
  int16_t x = PRIERE_X1 - textWidth(text) + 1;
  drawText(x, y, text, rgb, PRIERE_X0, PRIERE_X1);
}

// N'efface pas l'ecran : l'appelant s'en charge, cf. panneau_vols.ino.
static void renderPrieres(const Prieres &p) {
  // En-tete : mosquee a gauche, heure courante a droite
  drawText(PRIERE_X0, LINE1_Y, p.mosquee, RGB_SECONDAIRE, PRIERE_X0, PRIERE_X1);
  drawRight(LINE1_Y, p.heure, RGB_SECONDAIRE);

  for (int16_t x = PRIERE_X0; x <= PRIERE_X1; x++)
    px(x, PRIERE_RULE_Y, RGB_SEP);

  // Priere en cours ou a venir : en blanc des que le panneau prend la main,
  // pour qu'on voie d'un coup d'oeil que c'est le moment de partir
  uint32_t couleurNom = p.priseMain ? RGB_PRINCIPAL : RGB_ACCENT;
  char nom[16];
  snprintf(nom, sizeof(nom), "%s%s", p.nom, p.demain ? " +1" : "");
  drawText(PRIERE_X0, LINE2_Y, nom, couleurNom, PRIERE_X0, PRIERE_X1);
  drawRight(LINE2_Y, p.adhan, couleurNom);

  // Bas : iqama a gauche, compte a rebours a droite
  if (p.iqama[0] && strcmp(p.iqama, p.adhan) != 0) {
    char iqama[16];
    snprintf(iqama, sizeof(iqama), "IQAMA %s", p.iqama);
    drawText(PRIERE_X0, LINE3_Y, iqama, RGB_TEXTE, PRIERE_X0, PRIERE_X1);
  }
  if (p.enCours)
    drawRight(LINE3_Y, "EN COURS", RGB_PRINCIPAL);
  else
    drawRight(LINE3_Y, p.restant, RGB_TEXTE);
}

#endif  // ECRAN_PRIERES_H
