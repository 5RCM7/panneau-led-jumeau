// ecran_adkar.h - un nom d'Allah par jour, sa signification en defilement
//
// Jumeau d'ecran_adkar.py, ligne pour ligne.
//
//     ADKAR 12/99                 23:07     en-tete, rang du jour et heure
//             [arabe]                       le nom, centre
//     AL-AZIZ - LE TOUT PUISSANT - PUIS...  sens et signification, defilants
//
// Un nom par jour, et non un qui tourne a la minute : on a le temps de le
// retenir. C'est la passerelle qui designe le nom, dans le champ "ad", comme
// elle designe l'ecran : les deux cotes du jumeau montrent ainsi toujours le
// meme.
//
// Inclus depuis panneau_vols.ino APRES ecran_alerte.h (drawSprite) et
// adkar.h.

#ifndef ECRAN_ADKAR_H
#define ECRAN_ADKAR_H

// Mise en page - memes valeurs qu'ecran_adkar.py
static const int16_t ADKAR_X0 = 2;
static const int16_t ADKAR_X1 = WIDTH_PX - 3;
static const int16_t ADKAR_ENTETE_Y = 0;
static const int16_t ADKAR_MOT_Y = 9;
static const int16_t ADKAR_SENS_Y = 25;
static const float ADKAR_PX_PAR_SEC = 20.0f;
static const int16_t ADKAR_GAP = 14;
static const char *ADKAR_TITRE = "ADKAR";

// En-tete de gauche : le titre, et ou l'on en est dans les 99.
static void adkarEntete(int16_t rang, char *sortie, size_t taille) {
  if (ADKAR_COUNT <= 0) {
    snprintf(sortie, taille, "%s", ADKAR_TITRE);
    return;
  }
  int16_t n = ((rang % ADKAR_COUNT) + ADKAR_COUNT) % ADKAR_COUNT;
  snprintf(sortie, taille, "%s %d/%d", ADKAR_TITRE, n + 1, ADKAR_COUNT);
}

// Ligne defilante : translitteration, sens court, puis signification.
static void adkarTexteBas(const Adkar *e, char *sortie, size_t taille) {
  snprintf(sortie, taille, "%s - %s - %s", e->latin, e->sens, e->detail);
}

// N'efface pas l'ecran : l'appelant s'en charge, cf. panneau_vols.ino.
static void renderAdkar(int16_t rang, const char *heure, uint32_t nowMs) {
  const Adkar *e = adkarEntree(rang);
  if (!e) return;

  // En-tete : le titre et le rang a gauche, l'heure a droite. Le panneau
  // reste une horloge murale, quel que soit l'ecran.
  char titre[16];
  adkarEntete(rang, titre, sizeof(titre));
  drawText(ADKAR_X0, ADKAR_ENTETE_Y, titre, RGB_SECONDAIRE, ADKAR_X0,
           ADKAR_X1);
  if (heure && heure[0])
    drawText(ADKAR_X1 - textWidth(heure) + 1, ADKAR_ENTETE_Y, heure,
             RGB_SECONDAIRE, ADKAR_X0, ADKAR_X1);

  // Le nom en arabe, centre
  drawSpriteClip(e->motif, ADKAR_H_PX, e->largeur,
                 (WIDTH_PX - e->largeur) / 2, ADKAR_MOT_Y, RGB_PRINCIPAL,
                 ADKAR_X0, ADKAR_X1);

  // Sens et signification, defilants s'ils depassent la largeur
  char bas[160];
  adkarTexteBas(e, bas, sizeof(bas));
  int16_t large = textWidth(bas);
  if (large <= ADKAR_X1 - ADKAR_X0 + 1) {
    drawText((WIDTH_PX - large) / 2, ADKAR_SENS_Y, bas, RGB_ACCENT, ADKAR_X0,
             ADKAR_X1);
    return;
  }
  int16_t span = large + ADKAR_GAP;
  int16_t avance =
      (int16_t)fmodf(nowMs / 1000.0f * ADKAR_PX_PAR_SEC, (float)span);
  drawText(ADKAR_X0 - avance, ADKAR_SENS_Y, bas, RGB_ACCENT, ADKAR_X0,
           ADKAR_X1);
  drawText(ADKAR_X0 - avance + span, ADKAR_SENS_Y, bas, RGB_ACCENT, ADKAR_X0,
           ADKAR_X1);
}

#endif  // ECRAN_ADKAR_H
