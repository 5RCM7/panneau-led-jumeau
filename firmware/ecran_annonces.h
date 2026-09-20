// ecran_annonces.h - annonces de la mosquee, en bandeau defilant
//
// Jumeau d'ecran_annonces.py, ligne pour ligne.
//
//     MOSQUEE                     23:07     en-tete, mosquee et heure
//     CONFERENCE VENDREDI 20H * COURS...   bandeau defilant
//
// Meme langage visuel que l'ecran des horaires : en-tete discret, bandeau a
// l'echelle 2 en dessous.
//
// Les titres arrivent dans le champ "an", separes par des barres verticales.
// La passerelle les a deja nettoyes et tronques : ici on met en page.
//
// Inclus depuis panneau_vols.ino APRES ecran_heure.h (drawTextEchelle).

#ifndef ECRAN_ANNONCES_H
#define ECRAN_ANNONCES_H

// Mise en page - memes valeurs qu'ecran_annonces.py
static const int16_t ANNONCES_X0 = 2;
static const int16_t ANNONCES_X1 = WIDTH_PX - 3;
static const int16_t ANNONCES_BANDE_Y = 13;
static const int16_t ANNONCES_ECHELLE = 2;
static const int16_t ANNONCES_ENTRE = 18;
static const float ANNONCES_PX_PAR_SEC = 22.0f;
static const char *ANNONCES_SEPARATEUR = "*";

// Les titres tels que la passerelle les envoie, separes par '|'
static const char ANNONCES_SEP_CHAMP = '|';

// Le n-ieme titre de la chaine "an", ou une chaine vide au-dela.
static void annonceRang(const Prieres &p, int8_t rang, char *sortie,
                        size_t taille) {
  sortie[0] = '\0';
  const char *curseur = p.annonces;
  for (int8_t i = 0; curseur && *curseur; i++) {
    if (i == rang) {
      size_t n = 0;
      while (n + 1 < taille && curseur[n] && curseur[n] != ANNONCES_SEP_CHAMP) {
        sortie[n] = curseur[n];
        n++;
      }
      sortie[n] = '\0';
      return;
    }
    const char *barre = strchr(curseur, ANNONCES_SEP_CHAMP);
    curseur = barre ? barre + 1 : NULL;
  }
}

static int8_t annoncesCombien(const Prieres &p) {
  if (!p.annonces[0]) return 0;
  int8_t n = 1;
  for (const char *c = p.annonces; *c; ++c)
    if (*c == ANNONCES_SEP_CHAMP) n++;
  return n;
}

static int16_t largeurAnnonce(const char *titre) {
  return largeurEchelle(titre, ANNONCES_ECHELLE) + ANNONCES_ENTRE
      + largeurEchelle(ANNONCES_SEPARATEUR, ANNONCES_ECHELLE) + ANNONCES_ENTRE;
}

static void dessineAnnonce(int16_t x, const char *titre) {
  drawTextEchelleClip(x, ANNONCES_BANDE_Y, titre, RGB_PRINCIPAL,
                      ANNONCES_ECHELLE, ANNONCES_X0, ANNONCES_X1);
  x += largeurEchelle(titre, ANNONCES_ECHELLE) + ANNONCES_ENTRE;
  drawTextEchelleClip(x, ANNONCES_BANDE_Y, ANNONCES_SEPARATEUR,
                      RGB_SECONDAIRE, ANNONCES_ECHELLE, ANNONCES_X0,
                      ANNONCES_X1);
}

// N'efface pas l'ecran : l'appelant s'en charge, cf. panneau_vols.ino.
static void renderAnnonces(const Prieres &p, uint32_t nowMs) {
  // Pas d'annonce : rien a dessiner. panneau_vols.ino a deja redirige vers
  // un autre ecran, cette garde ne sert qu'a ne pas dessiner dans le vide.
  int8_t combien = annoncesCombien(p);
  if (combien <= 0) return;

  // En-tete : la mosquee a gauche, l'heure a droite. Le panneau reste une
  // horloge murale, quel que soit l'ecran.
  drawText(ANNONCES_X0, LINE1_Y, p.mosquee, RGB_SECONDAIRE, ANNONCES_X0,
           ANNONCES_X1);
  if (p.heure[0])
    drawText(ANNONCES_X1 - textWidth(p.heure) + 1, LINE1_Y, p.heure,
             RGB_SECONDAIRE, ANNONCES_X0, ANNONCES_X1);

  int16_t span = 0;
  char titre[48];
  for (int8_t rang = 0; rang < combien; rang++) {
    annonceRang(p, rang, titre, sizeof(titre));
    if (titre[0]) span += largeurAnnonce(titre);
  }
  if (span <= 0) return;

  int16_t avance = (int16_t)(fmodf(nowMs / 1000.0f * ANNONCES_PX_PAR_SEC,
                                   (float)span));
  int16_t depart = ANNONCES_X0 - avance;

  // Deux passages : le second bouche le trou pendant que le premier sort
  for (int8_t repetition = 0; repetition < 2; repetition++) {
    int16_t x = depart + repetition * span;
    if (x > ANNONCES_X1) break;
    for (int8_t rang = 0; rang < combien; rang++) {
      annonceRang(p, rang, titre, sizeof(titre));
      if (!titre[0]) continue;
      int16_t large = largeurAnnonce(titre);
      if (x + large > ANNONCES_X0) dessineAnnonce(x, titre);
      x += large;
    }
  }
}

#endif  // ECRAN_ANNONCES_H
