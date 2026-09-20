// ecran_meteo.h - le temps qu'il fait au-dessus de la maison
//
// Jumeau d'ecran_meteo.py, ligne pour ligne.
//
//     [icone]  18 C            icone, temperature, ressenti a droite
//     COUVERT                  temps qu'il fait
//     PARIS        4 KM/H    lieu et vent
//
// Inclus depuis panneau_vols.ino APRES icones_meteo.h et les primitives.

#ifndef ECRAN_METEO_H
#define ECRAN_METEO_H

// Mise en page - memes valeurs qu'ecran_meteo.py
static const int16_t METEO_X0 = 2;
static const int16_t METEO_X1 = WIDTH_PX - 3;
static const int16_t METEO_ICONE_Y = 1;
static const int16_t METEO_TEXTE_X = 24;
static const char *ANNONCE_METEO = "METEO";
static const char *ANNONCE_PLUIE = "PLUIE DANS";
// En deca on compte en minutes, au-dela on donne l'heure de debut
static const int16_t PLUIE_BIENTOT_MIN = 60;

struct Meteo {
  bool ok = false;
  int16_t temperature = 0;
  int16_t ressenti = 0;
  int16_t vent = -1;
  int8_t icone = -1;      // rang dans ICONES, cf. icones_meteo.h
  char texte[16] = "";    // COUVERT, ECLAIRCIES...
  char lieu[12] = "";
  char heure[8] = "";     // calculee par la passerelle, cf. ecran_heure.h
  int16_t pluieMin = -1;  // -1 : aucune averse en vue
  char pluieHeure[8] = "";
};

// "18" + glyphe degre + "C". Le degre est FONT_DEGRE, ajoute a la police
// pour cet ecran ; ne pas le remplacer par un 'o' ou une apostrophe.
static void formatTemperature(char *sortie, size_t taille, int16_t valeur) {
  snprintf(sortie, taille, "%d%cC", valeur, FONT_DEGRE);
}

// Alerte pluie de la ligne du bas, vide s'il n'en vient pas. Sous l'heure
// qui vient, un decompte parle mieux : on decide de sortir ou d'attendre.
// Plus loin, l'heure de debut se retient mieux.
static void textePluie(const Meteo &m, char *sortie, size_t taille) {
  sortie[0] = '\0';
  if (m.pluieMin < 0) return;
  if (m.pluieMin < PLUIE_BIENTOT_MIN || !m.pluieHeure[0])
    snprintf(sortie, taille, "PLUIE %d MIN", m.pluieMin);
  else
    snprintf(sortie, taille, "PLUIE %s", m.pluieHeure);
}

// Ligne d'annonce quand une averse approche, vide sinon.
static void annoncePluie(const Meteo &m, char *sortie, size_t taille) {
  sortie[0] = '\0';
  if (m.pluieMin < 0) return;
  snprintf(sortie, taille, "%s %d MIN", ANNONCE_PLUIE, m.pluieMin);
}

// N'efface pas l'ecran : l'appelant s'en charge, cf. panneau_vols.ino.
static void renderMeteo(const Meteo &m) {
  drawSprite(iconePourRang(m.icone), ICONE_H, ICONE_W, METEO_X0, METEO_ICONE_Y,
             RGB_TEXTE);

  char tampon[12];
  formatTemperature(tampon, sizeof(tampon), m.temperature);
  drawText(METEO_TEXTE_X, LINE1_Y, tampon, RGB_PRINCIPAL, METEO_X0, METEO_X1);

  if (m.ressenti != m.temperature) {
    char ressenti[14];
    char valeur[12];
    formatTemperature(valeur, sizeof(valeur), m.ressenti);
    snprintf(ressenti, sizeof(ressenti), "~%s", valeur);
    drawText(METEO_X1 - textWidth(ressenti) + 1, LINE1_Y, ressenti,
             RGB_SECONDAIRE, METEO_X0, METEO_X1);
  }

  drawText(METEO_X0, LINE2_Y, m.texte, RGB_ACCENT, METEO_X0, METEO_X1);
  if (m.heure[0])
    drawText(METEO_X1 - textWidth(m.heure) + 1, LINE2_Y, m.heure,
             RGB_SECONDAIRE, METEO_X0, METEO_X1);

  // Ligne 3 : lieu a gauche - sauf si une averse arrive, auquel cas elle
  // prend la place du lieu et passe en orange
  char pluie[16];
  textePluie(m, pluie, sizeof(pluie));
  if (pluie[0])
    drawText(METEO_X0, LINE3_Y, pluie, RGB_TEXTE, METEO_X0, METEO_X1);
  else
    drawText(METEO_X0, LINE3_Y, m.lieu, RGB_SECONDAIRE, METEO_X0, METEO_X1);

  if (m.vent >= 0) {
    char vent[12];
    snprintf(vent, sizeof(vent), "%d KM/H", m.vent);
    drawText(METEO_X1 - textWidth(vent) + 1, LINE3_Y, vent, RGB_TEXTE,
             METEO_X0, METEO_X1);
  }
}

// Abscisse de l'icone pendant l'annonce : elle entre et se pose au centre.
// Meme mouvement que la mosquee, et pour la meme raison : le temps qu'il fait
// ne traverse pas le ciel, il s'installe.
static int16_t positionIcone(float avancement) {
  int16_t arrivee = (WIDTH_PX - ICONE_W) / 2;
  return (int16_t)lroundf(WIDTH_PX + (arrivee - WIDTH_PX) * adoucis(avancement));
}

static void renderAlerteMeteo(const Meteo &m, float avancement) {
  drawSprite(iconePourRang(m.icone), ICONE_H, ICONE_W,
             positionIcone(avancement), METEO_ICONE_Y, RGB_TEXTE);

  char annonce[24];
  // L'averse qui approche vaut mieux qu'un rappel du nom de la commune
  annoncePluie(m, annonce, sizeof(annonce));
  if (!annonce[0])
    snprintf(annonce, sizeof(annonce), "%s %s", ANNONCE_METEO, m.lieu);
  drawCentre(LINE2_Y, annonce, RGB_PRINCIPAL);

  char valeur[12];
  formatTemperature(valeur, sizeof(valeur), m.temperature);
  char bas[32];
  snprintf(bas, sizeof(bas), "%s  %s", valeur, m.texte);
  drawCentre(LINE3_Y, bas, RGB_ACCENT);
}

#endif  // ECRAN_METEO_H
