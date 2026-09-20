// ecran_liaison.h - quand la passerelle ne repond plus
//
// Jumeau d'ecran_liaison.py, ligne pour ligne.
//
//         LIAISON PERDUE           ce qui se passe
//        HEURE NON FIABLE          ce que ca change
//          DEPUIS 4 MIN            depuis quand
//
// Le panneau n'a ni horloge sauvegardee ni client NTP : l'heure lui vient de
// la passerelle, comme le reste. Passerelle muette, heure figee - et une
// horloge murale qui affiche avec aplomb l'heure d'il y a vingt minutes est
// pire qu'un ecran noir, parce qu'on la croit.
//
// D'ou cet ecran plutot qu'un discret temoin dans un coin : il ne s'agit pas
// de signaler un detail, mais de retirer sa confiance a tout ce qui est
// affiche. C'est le seul ecran que le firmware impose de lui-meme, contre
// le champ "sc" : la passerelle ne peut pas signaler son propre silence.
//
// Inclus depuis panneau_vols.ino APRES ecran_alerte.h (drawCentre).

#ifndef ECRAN_LIAISON_H
#define ECRAN_LIAISON_H

// Mise en page et tempo - memes valeurs qu'ecran_liaison.py
static const uint32_t LIAISON_SEUIL_MS = 90000;
static const char *LIAISON_TITRE = "LIAISON PERDUE";
static const char *LIAISON_SOUS_TITRE = "HEURE NON FIABLE";
static const char *LIAISON_DEPUIS = "DEPUIS";

// Vrai quand le silence a assez dure pour qu'on ne croie plus rien.
static bool liaisonPerdue(uint32_t depuisMs) {
  return depuisMs >= LIAISON_SEUIL_MS;
}

// Duree du silence, en trois mots au plus.
static void liaisonFormatDepuis(uint32_t depuisMs, char *sortie,
                                size_t taille) {
  uint32_t minutes = depuisMs / 60000;
  if (minutes < 60)
    snprintf(sortie, taille, "%s %lu MIN", LIAISON_DEPUIS,
             (unsigned long)minutes);
  else
    snprintf(sortie, taille, "%s %luH", LIAISON_DEPUIS,
             (unsigned long)(minutes / 60));
}

// N'efface pas l'ecran : l'appelant s'en charge, cf. panneau_vols.ino.
static void renderLiaison(uint32_t depuisMs) {
  drawCentre(LINE1_Y, LIAISON_TITRE, RGB_PRINCIPAL);
  drawCentre(LINE2_Y, LIAISON_SOUS_TITRE, RGB_TEXTE);
  char depuis[24];
  liaisonFormatDepuis(depuisMs, depuis, sizeof(depuis));
  drawCentre(LINE3_Y, depuis, RGB_SECONDAIRE);
}

#endif  // ECRAN_LIAISON_H
