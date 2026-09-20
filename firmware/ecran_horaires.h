// ecran_horaires.h - horaires de priere en bandeau defilant, arabe et francais
//
// Jumeau d'ecran_horaires.py, ligne pour ligne.
//
//     MOSQUEE                           23:07     en-tete, mosquee et heure
//     [arabe] FAJR 05:55  [arabe] DOHR 13:45 ...  bande defilante
//
// Le bandeau enchaine les cinq prieres du jour, chacune annoncee en arabe
// puis en francais. La priere a venir est mise en valeur.
//
// Inclus depuis panneau_vols.ino APRES ecran_alerte.h (drawSprite),
// ecran_heure.h (drawTextEchelle) et arabe.h.

#ifndef ECRAN_HORAIRES_H
#define ECRAN_HORAIRES_H

// Mise en page - memes valeurs qu'ecran_horaires.py
static const int16_t HORAIRES_X0 = 2;
static const int16_t HORAIRES_X1 = WIDTH_PX - 3;
static const int16_t HORAIRES_BANDE_Y = 13;
static const int16_t HORAIRES_LATIN_DY = 1;
static const int16_t HORAIRES_ECHELLE = 2;
static const int16_t HORAIRES_GAP = 4;
static const int16_t HORAIRES_ENTRE = 14;
static const float HORAIRES_PX_PAR_SEC = 22.0f;

static const char *ABREGES[5] = {"FAJ", "DOH", "ASR", "MAG", "ICH"};
static const char *ABREGE_JOUMOUA = "JOU";

// Noms complets, dans l'ordre de horaires.NOMS : ils servent de cle pour
// retrouver la silhouette arabe, et s'affichent tels quels en latin.
static const char *NOMS_PRIERES[5] = {"FAJR", "DOHR", "ASR", "MAGHREB",
                                      "ICHA"};
static const char *NOM_JOUMOUA = "JOUMOUA";

static int16_t largeurBloc(const char *nom, const char *heure) {
  const MotArabe *ar = arabePour(nom);
  int16_t large = ar ? ar->largeur + HORAIRES_GAP : 0;
  char latin[24];
  snprintf(latin, sizeof(latin), "%s %s", nom, heure);
  return large + largeurEchelle(latin, HORAIRES_ECHELLE) + HORAIRES_ENTRE;
}

static void dessineBloc(int16_t x, const char *nom, const char *heure,
                        bool courante) {
  uint32_t couleurNom = courante ? RGB_PRINCIPAL : RGB_SECONDAIRE;
  uint32_t couleurHeure = courante ? RGB_ACCENT : RGB_TEXTE;

  const MotArabe *ar = arabePour(nom);
  if (ar) {
    drawSpriteClip(ar->motif, ARABE_H_PX, ar->largeur, x, HORAIRES_BANDE_Y,
                   couleurNom, HORAIRES_X0, HORAIRES_X1);
    x += ar->largeur + HORAIRES_GAP;
  }

  int16_t y = HORAIRES_BANDE_Y + HORAIRES_LATIN_DY;
  drawTextEchelleClip(x, y, nom, couleurNom, HORAIRES_ECHELLE, HORAIRES_X0,
                      HORAIRES_X1);
  x += largeurEchelle(nom, HORAIRES_ECHELLE);
  x += FONT_ADVANCE * HORAIRES_ECHELLE;  // l'espace avant l'heure
  drawTextEchelleClip(x, y, heure, couleurHeure, HORAIRES_ECHELLE,
                      HORAIRES_X0, HORAIRES_X1);
}

// Extrait le n-ieme HH:MM de la chaine "pt" envoyee par la passerelle.
static void heureRang(const Prieres &p, int8_t rang, char *sortie,
                      size_t taille) {
  sortie[0] = '\0';
  const char *curseur = p.horaires;
  for (int8_t i = 0; curseur && *curseur; i++) {
    if (i == rang) {
      size_t n = 0;
      while (n + 1 < taille && curseur[n] && curseur[n] != ',') {
        sortie[n] = curseur[n];
        n++;
      }
      sortie[n] = '\0';
      return;
    }
    const char *virgule = strchr(curseur, ',');
    curseur = virgule ? virgule + 1 : NULL;
  }
}

static const char *nomRang(const Prieres &p, int8_t rang) {
  if (rang == 1 && p.joumoua) return NOM_JOUMOUA;
  return (rang >= 0 && rang < 5) ? NOMS_PRIERES[rang] : "";
}

// N'efface pas l'ecran : l'appelant s'en charge, cf. panneau_vols.ino.
static void renderHoraires(const Prieres &p, uint32_t nowMs) {
  // En-tete : mosquee a gauche, heure a droite. Le panneau reste une horloge
  // murale, meme quand le bandeau occupe le reste de la hauteur.
  drawText(HORAIRES_X0, LINE1_Y, p.mosquee, RGB_SECONDAIRE, HORAIRES_X0,
           HORAIRES_X1);
  if (p.heure[0])
    drawText(HORAIRES_X1 - textWidth(p.heure) + 1, LINE1_Y, p.heure,
             RGB_SECONDAIRE, HORAIRES_X0, HORAIRES_X1);

  int16_t span = 0;
  for (int8_t rang = 0; rang < 5; rang++) {
    char heure[8];
    heureRang(p, rang, heure, sizeof(heure));
    if (!heure[0]) continue;
    span += largeurBloc(nomRang(p, rang), heure);
  }
  if (span <= 0) return;

  int16_t avance = (int16_t)(fmodf(nowMs / 1000.0f * HORAIRES_PX_PAR_SEC,
                                   (float)span));
  int16_t depart = HORAIRES_X0 - avance;

  // Deux passages : le second bouche le trou pendant que le premier sort
  for (int8_t repetition = 0; repetition < 2; repetition++) {
    int16_t x = depart + repetition * span;
    if (x > HORAIRES_X1) break;
    for (int8_t rang = 0; rang < 5; rang++) {
      char heure[8];
      heureRang(p, rang, heure, sizeof(heure));
      if (!heure[0]) continue;
      const char *nom = nomRang(p, rang);
      int16_t large = largeurBloc(nom, heure);
      if (x + large > HORAIRES_X0) dessineBloc(x, nom, heure, rang == p.rang);
      x += large;
    }
  }
}

#endif  // ECRAN_HORAIRES_H
